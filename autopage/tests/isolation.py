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
import os
import pty
import signal
import struct
import sys
import time
import termios


(LINES, COLUMNS) = (24, 80)


def _exit_code_from_status(status):
    if hasattr(os, 'waitstatus_to_exitcode'):
        return os.waitstatus_to_exitcode(status)
    if os.WIFEXITED(status):
        return os.WEXITSTATUS(status)
    if os.WIFSIGNALED(status):
        return -os.WTERMSIG(status)
    raise ValueError('Unknown wait status %r' % status)


class IsolationEnvironment:
    def __init__(self, pid, ptm_fd, err_fd=None):
        self._pid = pid

        self._ptm_fd = ptm_fd
        self._tty = os.fdopen(ptm_fd, 'r')

        self._err_fd = err_fd

        self._exit_code = None

    def interrupt(self):
        self.write(b'\x03')

    def write(self, data):
        os.write(self._ptm_fd, data)
        time.sleep(0.001)

    def readline(self):
        return self._tty.readline()

    def error_output(self):
        if self._err_fd is None:
            return ''
        with os.fdopen(self._err_fd, closefd=False) as errf:
            return errf.read()

    def close(self):
        os.kill(self._pid, signal.SIGTERM)
        pid, status = os.waitpid(self._pid, 0)
        self._exit_code = _exit_code_from_status(status)
        self._tty.close()

    def exit_code(self):
        return self._exit_code


class PagerControl:
    def __init__(self, isolation_env):
        self.env = isolation_env
        self._total_lines = 0

    def read_lines(self, count):
        for i in range(count):
            line = '\x1b[?'
            while line.startswith('\x1b[?'):
                line = self.env.readline()
            self._total_lines += 1
            yield line.replace('\x1b[m', '')

    def _lines_in_page(self):
        count = 0
        try:
            while True:
                line = '\x1b[?'
                while line.lstrip(' q').startswith('\x1b[?'):
                    line = self.env.readline()
                if '--More--' in line or line == '\x1b[K\n':
                    break
                count += 1
        except IOError:
            pass
        self._total_lines += count
        return count

    def advance(self):
        self.env.write(b' ')
        return self._lines_in_page()

    def quit(self):
        self.env.write(b'q')
        return self._lines_in_page()

    def total_lines(self):
        return self._total_lines


@contextlib.contextmanager
def isolate(child_function,
            stdin_fd=None, stdout_fd=None, stderr_fd=None,
            *,
            lines=LINES, columns=COLUMNS, stderr_to_tty=False):
    if stderr_fd is None and not stderr_to_tty:
        err_output_fd, stderr_fd = os.pipe()
    else:
        err_output_fd = None
    for fd in (stdin_fd, stdout_fd, stderr_fd):
        if fd is not None:
            os.set_inheritable(fd, True)

    env_pid, tty = pty.fork()
    if env_pid == 0:
        os.environ['TERM'] = 'xterm-256color'
        if stdin_fd is not None:
            sys.stdin = os.fdopen(stdin_fd)
        if stdout_fd is not None:
            sys.stdout = os.fdopen(stdout_fd, 'w')
        if stderr_fd is not None:
            sys.stderr = os.fdopen(stderr_fd, 'w', buffering=1)
        try:
            result = child_function()
        finally:
            sys.stdout.close()
            sys.stderr.close()
        os._exit(result or 0)
    else:
        for fd in (stdin_fd, stdout_fd, stderr_fd):
            if fd is not None:
                os.close(fd)
        fcntl.ioctl(tty, termios.TIOCSWINSZ,
                    struct.pack('HHHH', lines, columns, 0, 0))
        env = IsolationEnvironment(env_pid, tty, err_output_fd)
        time.sleep(0.05)
        try:
            yield env
        finally:
            time.sleep(0.001)
            if err_output_fd is not None:
                os.close(err_output_fd)
            env.close()
