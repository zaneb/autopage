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

"""
A library to provide automatic paging for console output.

By Zane Bitter.
"""

import contextlib
import enum
import io
import os
import signal
import subprocess
import sys

import types
import typing
from typing import Any, Optional, Type, Dict, TextIO

from autopage import command


__all__ = ['AutoPager', 'line_buffer_from_input']


class ErrorStrategy(enum.Enum):
    """
    The strategy for dealing with unicode errors when convering text to bytes.
    """
    STRICT = 'strict'
    IGNORE = 'ignore'
    REPLACE = 'replace'
    BACKSLASH_REPLACE = 'backslashreplace'
    XML_CHARREF_REPLACE = 'xmlcharrefreplace'
    NAME_REPLACE = 'namereplace'


class AutoPager:
    """
    A context manager that launches a pager for the output if appropriate.

    If the output stream is not to the console (i.e. it is piped or
    redirected), no pager will be launched.
    """

    def __init__(self,
                 output_stream: Optional[TextIO] = None, *,
                 pager_command: command.CommandType = command.DefaultPager(),
                 allow_color: bool = True,
                 line_buffering: Optional[bool] = None,
                 reset_on_exit: bool = False,
                 errors: Optional[ErrorStrategy] = None):
        self._use_stdout = output_stream is None or output_stream is sys.stdout
        self._out = sys.stdout if output_stream is None else output_stream
        self._tty = (not self._out.closed) and self._out.isatty()
        self._command = command.get_pager_command(pager_command)
        self._config = command.PagerConfig(
                color=allow_color,
                line_buffering_requested=bool(line_buffering),
                reset_terminal=reset_on_exit,
            )
        self._set_line_buffering = line_buffering
        self._set_errors = (ErrorStrategy(errors) if errors is not None
                            else None)
        self._pager: Optional[subprocess.Popen] = None
        self._exit_code = 0

    def to_terminal(self) -> bool:
        """Return whether the output stream is a terminal."""
        return self._tty

    def __enter__(self) -> TextIO:
        # Only invoke the pager if the output is going to a tty; if it is
        # being sent to a file or pipe then we don't want the pager involved
        if self.to_terminal() and self._command.command() != ['cat']:
            try:
                return self._paged_stream()
            except OSError:
                pass
        self._reconfigure_output_stream()
        return self._out

    def _line_buffering(self) -> bool:
        if self._set_line_buffering is None:
            return getattr(self._out, 'line_buffering', self._tty)
        return self._set_line_buffering

    def _encoding(self) -> str:
        return getattr(self._out, 'encoding', 'ascii')

    def _errors(self) -> str:
        if self._set_errors is None:
            return getattr(self._out, 'errors', ErrorStrategy.STRICT.value)
        return self._set_errors.value

    def _reconfigure_output_stream(self) -> None:
        if self._set_line_buffering is None and self._set_errors is None:
            return

        if not isinstance(self._out, io.TextIOWrapper):
            return

        # Python 3.7 & later
        if hasattr(self._out, 'reconfigure'):
            self._out.reconfigure(line_buffering=self._set_line_buffering,
                                  errors=(self._set_errors.value
                                          if self._set_errors is not None
                                          else None))
        # Python 3.6
        elif (self._out.line_buffering != self._line_buffering()
                or self._out.errors != self._errors()):
            # Pure-python I/O
            if (hasattr(self._out, '_line_buffering')
                    and hasattr(self._out, '_errors')):
                py_out = typing.cast(Any, self._out)
                py_out._line_buffering = self._line_buffering()
                py_out._errors = self._errors()
                py_out.flush()
            # Native C I/O
            else:
                encoding = self._encoding()
                errors = self._errors()
                line_buffering = self._line_buffering()
                try:
                    if self._use_stdout:
                        sys.stdout = typing.cast(TextIO, None)
                    newstream = io.TextIOWrapper(
                        self._out.detach(),
                        line_buffering=line_buffering,
                        encoding=encoding,
                        errors=errors)
                    self._out = newstream
                finally:
                    if self._use_stdout:
                        sys.stdout = self._out

    def _pager_env(self) -> Optional[Dict[str, str]]:
        new_vars = self._command.environment_variables(self._config)
        if not new_vars:
            return None

        env = dict(os.environ)
        env.update(new_vars)
        return env

    def _pager_out_stream(self) -> Optional[TextIO]:
        if not self._use_stdout:
            try:
                # Ensure the output stream has a file descriptor
                self._out.fileno()
            except OSError:
                pass
            else:
                return self._out
        return None

    def _paged_stream(self) -> TextIO:
        buffer_size = 1 if self._line_buffering() else -1
        self._pager = subprocess.Popen(self._command.command(),
                                       env=self._pager_env(),
                                       bufsize=buffer_size,
                                       universal_newlines=True,
                                       encoding=self._encoding(),
                                       errors=self._errors(),
                                       stdin=subprocess.PIPE,
                                       stdout=self._pager_out_stream())
        assert self._pager.stdin is not None
        return typing.cast(TextIO, self._pager.stdin)

    def __exit__(self,
                 exc_type: Optional[Type[BaseException]],
                 exc: Optional[BaseException],
                 traceback: Optional[types.TracebackType]) -> bool:
        if self._pager is not None:
            # Pager ignores Ctrl-C, so we should too
            with _sigint_ignore():
                pager_in = self._pager.stdin
                assert pager_in is not None
                try:
                    pager_in.close()
                except BrokenPipeError:
                    # Other end of pipe already closed
                    self._exit_code = _signal_exit_code(signal.SIGPIPE)
                # Wait for user to exit pager
                self._pager.wait()
        else:
            self._flush_output()
        return self._process_exception(exc)

    def _flush_output(self) -> None:
        try:
            if not self._out.closed:
                self._out.flush()
        except BrokenPipeError:
            self._exit_code = _signal_exit_code(signal.SIGPIPE)
            try:
                # Other end of pipe already closed, so close the stream now
                # and handle the error. If we leave the stream open with
                # unflushed data, then it will print an unhandleable
                # exception during Python's interpreter shutdown.
                self._out.close()
            except BrokenPipeError:
                # This will always happen
                pass

    def _process_exception(self, exc: Optional[BaseException]) -> bool:
        if exc is not None:
            if isinstance(exc, BrokenPipeError):
                self._exit_code = _signal_exit_code(signal.SIGPIPE)
                # Suppress exceptions caused by a broken pipe (indicating that
                # the user has exited the pager, or the following process in
                # the pipeline has exited)
                return True
            elif isinstance(exc, KeyboardInterrupt):
                self._exit_code = _signal_exit_code(signal.SIGINT)
            elif isinstance(exc, SystemExit) and isinstance(exc.code, int):
                self._exit_code = exc.code
            else:
                self._exit_code = 1
        return False

    def exit_code(self) -> int:
        """
        Return an appropriate exit code for the process based on any errors.

        If the user exits the program prematurely by closing the pager, we may
        want to return a different exit code for the process. This method
        returns an appropriate exit code on the basis of the existence and type
        of any uncaught exceptions.
        """
        return self._exit_code


def line_buffer_from_input(input_stream: Optional[typing.IO] = None) -> bool:
    """
    Return whether line buffering should be enabled for a given input stream.

    When data is being read from an input stream, processed somehow, and then
    written to an autopaged output stream, it may be desirable to enable line
    buffering on the output. This means that each line of data written to the
    output will be visible immediately, as opposed to waiting for the output
    buffer to fill up. This is, however, slower.

    If the input stream is a file, line buffering is unnecessary. This function
    determines whether an input stream might require line buffering on output.

    If no input stream is specified, sys.stdin is assumed.

        >>> with AutoPager(line_buffering=line_buffer_from_input()) as out:
        >>>     for l in sys.stdin:
        >>>         out.write(l)
    """
    if input_stream is None:
        input_stream = sys.stdin
    # On Illumos, TTYs claim to be seekable so don't believe them
    return not (input_stream.seekable() and not input_stream.isatty())


def _signal_exit_code(signum: signal.Signals) -> int:
    """
    Return the exit code corresponding to a received signal.

    Conventionally, when a program exits due to a signal its exit code is 128
    plus the signal number.
    """
    return 128 + int(signum)


@contextlib.contextmanager
def _sigint_ignore() -> typing.Generator[None, None, None]:
    """
    Context manager to temporarily ignore SIGINT.
    """
    old_int_handler: Any = None
    try:
        old_int_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
        yield
    finally:
        # If this is called from a finalizer during interpreter shutdown,
        # CPython will have removed the definition of SIG_IGN, so we can't
        # set the signal handler back to anything. We can detect this by
        # checking for None returned from getsignal()
        if signal.getsignal(signal.SIGINT) is not None:
            signal.signal(signal.SIGINT, old_int_handler)
