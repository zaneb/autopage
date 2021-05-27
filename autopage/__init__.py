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

import asyncio
import codecs
import enum
import io
import os
import signal
import subprocess
import sys

import types
import typing
from typing import Any, Optional, Type, Dict, List, TextIO

_SignalHandler = typing.Callable[[signal.Signals, types.FrameType], Any]

_SIGNAL_EXIT_BASE = 128

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
                 allow_color: bool = True,
                 line_buffering: Optional[bool] = None,
                 reset_on_exit: bool = False,
                 errors: Optional[ErrorStrategy] = None):
        self._use_stdout = output_stream is None or output_stream is sys.stdout
        self._out = sys.stdout if output_stream is None else output_stream
        self._tty = self._out.isatty()
        self._color = allow_color
        self._reset = reset_on_exit
        self._set_line_buffering = line_buffering
        self._set_errors = (ErrorStrategy(errors) if errors is not None
                            else None)
        self._pager: Optional[subprocess.Popen] = None
        self._async_stream: Optional[TextIO] = None
        self._async_pager: Optional[asyncio.subprocess.Process] = None
        self._exit_code = 0

    def to_terminal(self) -> bool:
        """Return whether the output stream is a terminal."""
        return self._tty

    def __enter__(self) -> TextIO:
        # Only invoke the pager if the output is going to a tty; if it is
        # being sent to a file or pipe then we don't want the pager involved
        if self.to_terminal():
            try:
                return self._paged_stream()
            except OSError:
                pass
        self._reconfigure_output_stream()
        return self._out

    async def __aenter__(self) -> TextIO:
        # Only invoke the pager if the output is going to a tty; if it is
        # being sent to a file or pipe then we don't want the pager involved
        if self.to_terminal():
            try:
                return await self._paged_async_stream()
            except OSError:
                pass
        self._reconfigure_output_stream()
        return self._out

    def _line_buffering(self) -> bool:
        if self._set_line_buffering is None:
            return getattr(self._out, 'line_buffering', False)
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
        out = typing.cast(io.TextIOWrapper, self._out)

        # Python 3.7 & later
        if hasattr(out, 'reconfigure'):
            out.reconfigure(line_buffering=self._set_line_buffering,
                            errors=(self._set_errors.value
                                    if self._set_errors is not None
                                    else None))
        # Python 3.6
        elif (self._out.line_buffering != self._line_buffering()
                or self._out.errors != self._errors()):
            # Pure-python I/O
            if (hasattr(out, '_line_buffering')
                    and hasattr(out, '_errors')):
                py_out = typing.cast(Any, out)
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
                        out.detach(),
                        line_buffering=line_buffering,
                        encoding=encoding,
                        errors=errors)
                    self._out = newstream
                finally:
                    if self._use_stdout:
                        sys.stdout = self._out

    def _pager_cmd(self) -> List[str]:
        pager = os.getenv('PAGER')
        if pager is not None:
            import shlex
            return shlex.split(pager)
        return ['less']

    def _pager_env(self) -> Optional[Dict[str, str]]:
        less_flags = []
        lv_flags = []
        if self._color:
            # This option will cause less to output ANSI color escape sequences
            # in raw form.
            # Equivalent to the --RAW-CONTROL-CHARS argument
            less_flags.append('R')
            # This option allows ANSI color escape sequences in lv
            lv_flags.append('-c')
        if not self._line_buffering() and not self._reset:
            # This option will cause less to buffer until an entire screen's
            # worth of data is available (or the EOF is reached), so don't
            # enable it when line buffering is requested. It also does not
            # reset the terminal after exiting, so don't enable it when
            # resetting the terminal is requested.
            # Equivalent to the --quit-if-one-screen argument
            less_flags.append('F')
        if not self._reset:
            # This option will cause less to not reset the terminal after
            # exiting.
            # Equivalent to the --no-init argument
            less_flags.append('X')

        env = dict(os.environ)
        if less_flags and (os.getenv('LESS') is None):
            env['LESS'] = ''.join(less_flags)
        if lv_flags and (os.getenv('LV') is None):
            env['LV'] = ' '.join(lv_flags)
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
        self._pager = subprocess.Popen(self._pager_cmd(),
                                       env=self._pager_env(),
                                       bufsize=buffer_size,
                                       universal_newlines=True,
                                       encoding=self._encoding(),
                                       errors=self._errors(),
                                       stdin=subprocess.PIPE,
                                       stdout=self._pager_out_stream())
        assert self._pager.stdin is not None
        return typing.cast(TextIO, self._pager.stdin)

    async def _handle_async_pager_exit(self, task: asyncio.Task) -> None:
        assert self._async_pager is not None
        await self._async_pager.wait()
        task.cancel('Pager exited')

    def _interrupt_handler(self, task: asyncio.Task) -> _SignalHandler:
        def handle_interrupt(signum: signal.Signals,
                             frame: types.FrameType) -> None:
            if not task.done():
                task.cancel('SIGINT received')

        return handle_interrupt

    async def _paged_async_stream(self) -> TextIO:
        self._async_pager = await asyncio.create_subprocess_exec(
            *self._pager_cmd(),
            stdin=asyncio.subprocess.PIPE,
            stdout=self._pager_out_stream(),
            env=self._pager_env())
        loop = asyncio.get_running_loop()
        current_task = asyncio.current_task(loop)
        assert current_task is not None
        cleanup = loop.create_task(self._handle_async_pager_exit(current_task))
        self._async_cleanup_task = cleanup
        new_int_handler = self._interrupt_handler(current_task)
        self._old_int_handler = signal.signal(signal.SIGINT, new_int_handler)

        stdin_bytes = typing.cast(typing.BinaryIO, self._async_pager.stdin)
        streamWriter = codecs.getwriter(self._encoding())
        streamReader = codecs.getreader(self._encoding())
        self._async_stream = codecs.StreamReaderWriter(stdin_bytes,
                                                       streamReader,
                                                       streamWriter,
                                                       errors=self._errors())
        return self._async_stream

    def __exit__(self,
                 exc_type: Optional[Type[BaseException]],
                 exc: Optional[BaseException],
                 traceback: Optional[types.TracebackType]) -> bool:
        if self._pager is not None:
            try:
                typing.cast(TextIO, self._pager.stdin).close()
            except BrokenPipeError:
                # Other end of pipe already closed
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
        else:
            self._flush_output()
        return self._process_exception(exc)

    async def __aexit__(self,
                        exc_type: Optional[Type[BaseException]],
                        exc: Optional[BaseException],
                        traceback: Optional[types.TracebackType]) -> bool:
        try:
            if self._async_pager is not None:
                self._async_cleanup_task.cancel()

                try:
                    if self._async_pager.stdin is not None:
                        if sys.version_info >= (3, 7):
                            if not self._async_pager.stdin.is_closing():
                                await self._async_pager.stdin.drain()
                            if self._async_stream is not None:
                                self._async_stream.close()
                            await self._async_pager.stdin.wait_closed()
                        else:
                            await self._async_pager.stdin.drain()
                except ConnectionResetError:
                    # Other end of pipe already closed
                    pass
                # Wait for user to exit pager
                await self._async_pager.wait()
            else:
                self._flush_output()
            return self._process_exception(exc)
        finally:
            if (self._old_int_handler is not None
                    and signal.getsignal(signal.SIGINT) is not None):
                signal.signal(signal.SIGINT, self._old_int_handler)

    def _flush_output(self) -> None:
        try:
            if not self._out.closed:
                self._out.flush()
        except BrokenPipeError:
            try:
                # Other end of pipe already closed, so close the stream now
                # and handle the error.
                self._out.close()
            except BrokenPipeError:
                # This will always happen
                pass

    def _process_exception(self, exc: Optional[BaseException]) -> bool:
        if exc is not None:
            if isinstance(exc, (BrokenPipeError, asyncio.CancelledError)):
                # Exit code for SIGPIPE
                self._exit_code = _SIGNAL_EXIT_BASE + 13
                # Suppress exceptions caused by a broken pipe (indicating that
                # the user has exited the pager, or the following process in
                # the pipeline has exited)
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
