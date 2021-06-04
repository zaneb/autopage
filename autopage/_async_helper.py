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

import asyncio
import codecs
import os
import sys

import types
import typing
from typing import Any, Optional, Union, Type
from typing import IO, Mapping, Sequence, Generator


_Arg = Union[str, bytes, os.PathLike]
_File = Union[int, IO[Any]]


SUBPROCESS_EXITED_CANCEL_MSG = "Subprocess exited"


class _AsyncProcess:
    def __init__(self,
                 proc: asyncio.subprocess.Process,
                 cleanup_task: asyncio.Task,
                 *,
                 text: bool,
                 encoding: Optional[str],
                 errors: Optional[str]):
        self._proc = proc
        self._cleanup_task = cleanup_task

        self._text = text
        self._encoding = encoding if encoding is not None else 'utf-8'
        self._errors = errors if errors is not None else 'strict'

        self.__closing = False
        self.stdin = self._make_io(proc.stdin)
        self.stdout = self._make_io(proc.stdout)
        self.stderr = self._make_io(proc.stderr)

    async def wait(self) -> None:
        if self.stdout is not None:
            self.stdout.close()
        if self.stderr is not None:
            self.stderr.close()

        self._cleanup_task.cancel()

        await self._proc.wait()

    async def stdin_flush(self) -> None:
        if self.__closing:
            raise ValueError("stdin already closed")

        stdin = self._proc.stdin
        if stdin is None:
            return

        if sys.version_info >= (3, 7) and stdin.is_closing():
            raise BrokenPipeError

        try:
            await stdin.drain()
        except ConnectionResetError:
            # Other end of pipe already closed
            raise BrokenPipeError

    async def stdin_close(self) -> None:
        if self.__closing:
            return

        raw_stream = self._proc.stdin
        if raw_stream is None:
            return

        try:
            await self.stdin_flush()
        finally:
            self.__closing = True

            try:
                text_stream = self.stdin if self._text else None
                if text_stream is not None:
                    text_stream.close()
                else:
                    raw_stream.close()

                if sys.version_info >= (3, 7):
                    await raw_stream.wait_closed()
            except ConnectionResetError:
                # Other end of pipe already closed
                pass

    def _make_io(self,
                 bytestream: Union[None,
                                   asyncio.StreamReader,
                                   asyncio.StreamWriter]) -> Optional[IO[Any]]:
        if bytestream is None:
            return bytestream
        io = typing.cast(typing.BinaryIO, bytestream)
        if not self._text:
            return io

        streamWriter = codecs.getwriter(self._encoding)
        streamReader = codecs.getreader(self._encoding)
        return codecs.StreamReaderWriter(io,
                                         streamReader,
                                         streamWriter,
                                         errors=self._errors)


class AsyncPopen:
    def __init__(self,
                 args: Sequence[_Arg],
                 stdin: Optional[_File] = None,
                 stdout: Optional[_File] = None,
                 stderr: Optional[_File] = None,
                 env: Optional[Mapping[str, str]] = None,
                 *,
                 encoding: Optional[str] = None,
                 errors: Optional[str] = None,
                 text: Optional[bool] = None):
        self._text = text if text is not None else True
        self._encoding = encoding
        self._errors = errors
        self._subproc = asyncio.create_subprocess_exec(
            *args,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            env=env)

        self._process_context: Optional[_AsyncProcess] = None

    def __await__(self) -> Generator[Any, None, _AsyncProcess]:
        return self.start().__await__()

    async def start(self) -> _AsyncProcess:
        subproc = await self._subproc

        async def handle_exit(process: asyncio.subprocess.Process,
                              task: asyncio.Task) -> None:
            await process.wait()
            task.cancel(SUBPROCESS_EXITED_CANCEL_MSG)

        loop = asyncio.get_running_loop()
        current_task = asyncio.current_task(loop)
        assert current_task is not None
        cleanup = loop.create_task(handle_exit(subproc, current_task))

        return _AsyncProcess(subproc, cleanup,
                             text=self._text,
                             encoding=self._encoding,
                             errors=self._errors)

    async def __aenter__(self) -> _AsyncProcess:
        self._process_context = await self
        return self._process_context

    async def __aexit__(self,
                        exc_type: Optional[Type[BaseException]],
                        exc: Optional[BaseException],
                        traceback: Optional[types.TracebackType]) -> bool:
        assert self._process_context is not None
        try:
            await self._process_context.stdin_close()
        except BrokenPipeError:
            pass
        finally:
            await self._process_context.wait()
        return False


__all__ = ['AsyncPopen']
