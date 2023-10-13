#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.

import contextlib
import fcntl
import itertools
import multiprocessing
import os
import pty
import re
import signal
import struct
import sys
import tempfile
import termios
import time
import traceback

import types
from typing import Optional, Generator, Tuple
import typing


(LINES, COLUMNS) = (24, 80)


def _open_fifo(path: Optional[str],
               write: bool) -> Optional[int]:
    if path is None:
        return None
    return os.open(path, os.O_WRONLY if write else os.O_RDONLY)


class IsolationEnvironment:
    def __init__(self, pid: int, ptm_fd: int,
                 stdin_fifo: Optional[str] = None,
                 stdout_fifo: Optional[str] = None,
                 stderr_fifo: Optional[str] = None):
        self._pid = pid

        self._ptm_fd = ptm_fd
        self._tty = os.fdopen(ptm_fd, 'r')

        self._stdin_fifo_fd = _open_fifo(stdin_fifo, True)
        self._stdout_fifo_fd = _open_fifo(stdout_fifo, False)
        self._stderr_fifo_fd = _open_fifo(stderr_fifo, False)

        self._exit_code: Optional[int] = None

        self._raw_lines: typing.List[str] = []
        self._lines: typing.List[str] = []

    def interrupt(self) -> None:
        self.write(b'\x03')

    def write(self, data: bytes) -> None:
        os.write(self._ptm_fd, data)
        time.sleep(0.001)

    def readline(self) -> str:
        line = self._tty.readline()
        self._raw_lines.append(line)
        return line

    def error_output(self) -> str:
        if self._stderr_fifo_fd is None:
            return ''
        with os.fdopen(self._stderr_fifo_fd) as errf:
            self._stderr_fifo_fd = None
            return errf.read()

    def stdout_pipe(self) -> typing.TextIO:
        assert self._stdout_fifo_fd is not None
        stdout = os.fdopen(self._stdout_fifo_fd)
        self._stdout_fifo_fd = None
        return stdout

    def stdin_pipe(self) -> typing.TextIO:
        assert self._stdin_fifo_fd is not None
        return os.fdopen(self._stdin_fifo_fd, 'w', closefd=False)

    def close(self, get_return_code: typing.Callable[[], int]) -> None:
        for i in range(100):
            if os.waitpid(self._pid, os.WNOHANG) != (0, 0):
                break
            time.sleep(0.001)
        else:
            os.kill(self._pid, signal.SIGTERM)
            os.waitpid(self._pid, 0)
        self._exit_code = get_return_code()
        self._tty.close()
        for fifo_fd in (self._stdin_fifo_fd,
                        self._stdout_fifo_fd,
                        self._stderr_fifo_fd):
            if fifo_fd is not None:
                os.close(fifo_fd)

    def exit_code(self) -> int:
        assert self._exit_code is not None
        return self._exit_code

    def record_output(self, line: str) -> None:
        self._lines.append(line)

    def recorded_output(self) -> typing.Tuple[typing.List[str],
                                              typing.List[str]]:
        return self._raw_lines[:], self._lines[:]


class PagerControl:
    _page_end = None
    _ctrl_chars = re.compile(r'\x1b\['
                             r'(\?|[0-2]?K|[0-9]*;?[0-9]*H|[0-3]?J|[0-9]*m)')

    def __init__(self, isolation_env: IsolationEnvironment):
        self.env = isolation_env
        self._total_lines = 0
        self._lines = self._iter_lines()

    def _iter_lines(self) -> Generator[typing.Union[str, None],
                                       None, None]:
        def get_content(segment: str) -> Tuple[bool,
                                               typing.Union[str, None]]:
            if not segment:
                return False, ''
            if segment == '\x1b[1m~\x1b[0m\n':
                # Ignore lines that are filling blank vertical space with
                # '~' after hitting Ctrl-C when the screen is not full
                return False, ''
            visible = self._ctrl_chars.sub('', segment)
            if ((visible.rstrip() == ':' or '(END)' in visible
                    or 'Waiting for data...' in visible)
                    and segment.replace('\x1b[m', '') != visible):
                return True, self._page_end
            elif visible.rstrip() or segment == visible:
                self._total_lines += 1
                self.env.record_output(visible)
                return True, visible
            return False, ''

        while True:
            line = '\x1b[?'
            while line.lstrip(' q').startswith('\x1b[?'):
                rawline = self.env.readline()
                line = (rawline.replace('\x07', '')     # Ignore bell
                               .replace('\x1b[m', ''))  # Ignore style reset
            before, reset, after = line.partition('\x1b[2J')

            valid, content = get_content(before)
            if valid:
                yield content
            if reset and not (valid and (content is self._page_end)):
                yield self._page_end
            valid, content = get_content(after)
            if valid:
                yield content

    def read_lines(self, count: int) -> typing.Iterator[str]:
        return itertools.islice((line for line in self._lines
                                 if line is not self._page_end), count)

    def _lines_in_page(self) -> int:
        original_count = self._total_lines
        try:
            for line in self._lines:
                if line is self._page_end:
                    break
        except IOError:
            pass
        return self._total_lines - original_count

    def advance(self) -> int:
        self.env.write(b' ')
        return self._lines_in_page()

    def quit(self) -> int:
        self.env.write(b'q')
        return self._lines_in_page()

    def total_lines(self) -> int:
        return self._total_lines


@contextlib.contextmanager
def _fifo(fifo_path: str) -> Generator[str, None, None]:
    try:
        os.mkfifo(fifo_path, 0o600)
        yield fifo_path
    finally:
        try:
            os.unlink(fifo_path)
        except OSError:
            pass


@contextlib.contextmanager
def _fifos(*fifo_names: Optional[str]) -> Generator[typing.List[Optional[str]],
                                                    None, None]:
    with tempfile.TemporaryDirectory() as directory:
        with contextlib.ExitStack() as stack:
            fifos = [stack.enter_context(_fifo(os.path.join(directory,
                                                            name)))
                     if name is not None else None
                     for name in fifo_names]
            yield fifos


class TestProcessNotComplete(Exception):
    pass


class TimeoutException(Exception):
    def __init__(self, pid: Optional[int]):
        super(Exception, self).__init__(f'Test process {pid} timed out')


@contextlib.contextmanager
def isolate(child_function: typing.Callable[[], int],
            stdin_pipe: bool = False,
            stdout_pipe: bool = False,
            stderr_pipe: bool = True,
            *,
            lines: int = LINES,
            columns: int = COLUMNS) -> Generator[IsolationEnvironment,
                                                 None, None]:
    with _fifos('stdin' if stdin_pipe else None,
                'stdout' if stdout_pipe else None,
                'stderr' if stderr_pipe else None) as fifo_paths:
        result_r, result_w = os.pipe()
        env_pid, tty = pty.fork()
        if env_pid == pty.CHILD:
            try:
                os.close(result_r)
                # Get ttyname from original stdout, even if test runner has
                # replaced stdout with another file
                pts = os.ttyname(pty.STDOUT_FILENO)

                ctx = multiprocessing.get_context('spawn')
                p = ctx.Process(target=_run_test, args=(child_function, pts,
                                                        *fifo_paths))
                p.start()

                def handle_terminate(signum: int,
                                     frame: Optional[types.FrameType]) -> None:
                    if p.is_alive():
                        p.terminate()

                signal.signal(signal.SIGTERM, handle_terminate)
                # Signals from the pty are for the test process, not us
                signal.signal(signal.SIGINT, signal.SIG_IGN)

                p.join(2)  # Wait at most 2s
                if p.exitcode is None:
                    raise TimeoutException(p.pid)
            except BaseException:
                try:
                    with os.fdopen(result_w, 'w') as result_writer:
                        traceback.print_exc(file=result_writer)
                finally:
                    # Prevent blocking in parent process by opening our end of
                    # all FIFOs.
                    for path, write in zip(fifo_paths, [False, True, True]):
                        _open_fifo(path, write)
                    os._exit(1)
            with os.fdopen(result_w, 'w') as result_writer:
                result_writer.write(f'{p.exitcode}\n')

            os._exit(0)
        else:
            os.close(result_w)
            fcntl.ioctl(tty, termios.TIOCSWINSZ,
                        struct.pack('HHHH', lines, columns, 0, 0))
            env = IsolationEnvironment(env_pid, tty, *fifo_paths)
            time.sleep(0.01)
            try:
                try:
                    yield env
                finally:
                    def get_return_code() -> int:
                        with os.fdopen(result_r) as result_reader:
                            result = result_reader.readline().rstrip()
                            try:
                                return int(result)
                            except ValueError:
                                pass
                            trace = result_reader.read()
                            raise TestProcessNotComplete('\n'.join([result,
                                                                    trace]))

                    env.close(get_return_code)
            except Exception:
                raw, processed = env.recorded_output()
                if raw:
                    print(f'Raw output: {repr(raw)}', file=sys.stderr)
                if processed:
                    print(f'Recorded output: {repr(processed)}',
                          file=sys.stderr)
                raise


def _run_test(test_function: typing.Callable[[], int],
              pts: str,
              stdin_fifo: Optional[str],
              stdout_fifo: Optional[str],
              stderr_fifo: Optional[str]) -> typing.NoReturn:
    os.environ['TERM'] = 'xterm-256color'

    tty_fd = os.open(pts, os.O_RDWR)
    if stdin_fifo is not None:
        old_stdin, sys.stdin = sys.stdin, open(stdin_fifo)
        old_stdin.close()
    else:
        os.dup2(tty_fd, pty.STDIN_FILENO)
    if stdout_fifo is not None:
        old_stdout, sys.stdout = sys.stdout, open(stdout_fifo, 'w')
        old_stdout.close()
    else:
        os.dup2(tty_fd, pty.STDOUT_FILENO)
    if stderr_fifo is not None:
        old_stderr, sys.stderr = sys.stderr, open(stderr_fifo, 'w',
                                                  buffering=1)
        old_stderr.close()
    else:
        os.dup2(tty_fd, pty.STDERR_FILENO)
    os.close(tty_fd)

    result = test_function()
    sys.exit(result or 0)
