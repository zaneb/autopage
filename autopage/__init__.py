#!/usr/bin/env python3

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

import io
import subprocess
import sys

import types
import typing
from typing import Any, Optional, Type, TextIO

_SIGNAL_EXIT_BASE = 128

__all__ = ['AutoPager', 'line_buffer_from_input']


class AutoPager:
    """
    A context manager that launches a pager for the output if appropriate.

    If the output stream is not to the console (i.e. it is piped or
    redirected), no pager will be launched.
    """

    def __init__(self,
                 output_stream: Optional[TextIO] = None, *,
                 line_buffering: bool = False):
        self._use_stdout = output_stream is None or output_stream is sys.stdout
        self._out = sys.stdout if output_stream is None else output_stream
        self._tty = self._out.isatty()
        self._line_buffering = line_buffering
        self._pager: Optional[subprocess.Popen] = None
        self._exit_code = 0

    def to_terminal(self) -> bool:
        """Return whether the output stream is a terminal."""
        return self._tty

    def __enter__(self) -> TextIO:
        # Only invoke the pager if the output is going to a tty; if it is
        # being sent to a file or pipe then we don't want the pager involved
        if self.to_terminal():
            return self._paged_stream()
        else:
            self._reconfigure_output_stream()
            return self._out

    def _reconfigure_output_stream(self) -> None:
        out = typing.cast(io.TextIOWrapper, self._out)
        if self._line_buffering:
            # Python 3.7 & later
            if hasattr(out, 'reconfigure'):
                out.reconfigure(line_buffering=self._line_buffering)
            else:
                # Pure-python I/O
                if hasattr(out, '_line_buffering'):
                    typing.cast(Any,
                                out)._line_buffering = self._line_buffering
                    out.flush()
                # Native I/O on Python 3.6
                elif (isinstance(out, io.TextIOWrapper) and
                        not out.line_buffering):
                    encoding = out.encoding
                    errors = out.errors
                    if self._use_stdout:
                        sys.stdout = typing.cast(TextIO, None)
                    newstream = io.TextIOWrapper(
                        out.detach(),
                        line_buffering=self._line_buffering,
                        encoding=encoding,
                        errors=errors)
                    self._out = newstream
                    if self._use_stdout:
                        sys.stdout = newstream

    def _paged_stream(self) -> TextIO:
        args = ['--RAW-CONTROL-CHARS']  # Enable colour output
        if not self._line_buffering:
            args.append('--quit-if-one-screen')
        buffer_size = 1 if self._line_buffering else -1
        out_stream: Optional[TextIO] = None
        if not self._use_stdout:
            try:
                # Ensure the output stream has a file descriptor
                self._out.fileno()
            except OSError:
                pass
            else:
                out_stream = self._out
        self._pager = subprocess.Popen(['less'] + args,
                                       bufsize=buffer_size,
                                       universal_newlines=True,
                                       errors='backslashreplace',
                                       stdin=subprocess.PIPE,
                                       stdout=out_stream)
        assert self._pager.stdin is not None
        return typing.cast(TextIO, self._pager.stdin)

    def __exit__(self,
                 exc_type: Optional[Type[BaseException]],
                 exc: Optional[BaseException],
                 traceback: Optional[types.TracebackType]) -> bool:
        if self._pager is not None:
            try:
                typing.cast(TextIO, self._pager.stdin).close()
            except BrokenPipeError:
                # Stream already closed
                pass
            # Wait for user to exit pager
            while True:
                try:
                    self._pager.wait()
                except KeyboardInterrupt:
                    # Pager ignores Ctrl-C, so we should too
                    continue
                else:
                    break

        if exc is not None:
            if isinstance(exc, BrokenPipeError):
                # Exit code for SIGPIPE
                self._exit_code = _SIGNAL_EXIT_BASE + 13
                # Suppress exceptions caused by a broken pipe (indicating that
                # the user has exited the pager
                if self._pager is not None:
                    return True
            elif isinstance(exc, KeyboardInterrupt):
                # Exit code for SIGINT
                self._exit_code = _SIGNAL_EXIT_BASE + 2
            elif isinstance(exc, SystemExit):
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
    return not input_stream.seekable()
