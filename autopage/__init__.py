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

import contextlib
import io
import subprocess
import sys


__all__ = ['AutoPager']


@contextlib.contextmanager
def AutoPager(output_stream=None, line_buffer=False):
    """
    A context manager that launches a pager for the output if appropriate.

    If the output stream is not to the console (i.e. it is piped or
    redirected), no pager will be launched.
    """
    use_stdout = output_stream is None
    if use_stdout:
        output_stream = sys.stdout

    if not output_stream.isatty():
        if line_buffer:
            # Python 3.7 & later
            if hasattr(output_stream, 'reconfigure'):
                output_stream.reconfigure(line_buffering=line_buffer)
            else:
                # Pure-python I/O
                if hasattr(output_stream, '_line_buffering'):
                    output_stream._line_buffering = line_buffer
                    output_stream.flush()
                # Native I/O on Python 3.6
                elif (isinstance(output_stream, io.TextIOWrapper) and
                        not output_stream.line_buffering):
                    args = {
                        'encoding': output_stream.encoding,
                        'errors': output_stream.errors,
                    }
                    if use_stdout:
                        sys.stdout = None
                    newstream = io.TextIOWrapper(output_stream.detach(),
                                                 line_buffering=line_buffer,
                                                 **args)
                    output_stream = newstream
                    if use_stdout:
                        sys.stdout = newstream
        yield output_stream
        return

    streams = {} if use_stdout else {'stdout': output_stream}
    streams['stdin'] = subprocess.PIPE
    args = ['--RAW-CONTROL-CHARS']  # Enable colour output
    if not line_buffer:
        args.append('--quit-if-one-screen')
    pager = subprocess.Popen(['less'] + args,
                             bufsize=1 if line_buffer else -1,
                             errors='backslashreplace',
                             **streams)
    try:
        with contextlib.closing(pager.stdin) as stream:
            yield stream
    except OSError:
        pass
    finally:
        while True:
            try:
                pager.wait()
                break
            except KeyboardInterrupt:
                # Pager ignores Ctrl-C, so we should too
                pass
