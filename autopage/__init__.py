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


__all__ = ['AutoPager']


@contextlib.contextmanager
def AutoPager(output_stream, line_buffer=False):
    """
    A context manager that launches a pager for the output if appropriate.

    If the output stream is not to the console (i.e. it is piped or
    redirected), no pager will be launched.
    """
    if not output_stream.isatty():
        if line_buffer:
            output_stream.reconfigure(line_buffering=line_buffer)
        yield output_stream
        return

    pager = subprocess.Popen(['less', '-R', '-F'],
                             stdin=subprocess.PIPE)
    try:
        with io.TextIOWrapper(pager.stdin,
                              line_buffering=line_buffer,
                              errors='backslashreplace') as stream:
            try:
                yield stream
            except KeyboardInterrupt:
                pass
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
