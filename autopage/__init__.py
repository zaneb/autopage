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
def AutoPager(output_stream):
    if not output_stream.isatty():
        yield output_stream
        return

    pager = subprocess.Popen(['less', '-R'],
                             stdin=subprocess.PIPE)
    try:
        with io.TextIOWrapper(pager.stdin,
                              errors='backslashreplace') as stream:
            try:
                yield stream
            except KeyboardInterrupt:
                pass
    except OSError:
        pass
    while True:
        try:
            pager.wait()
            break
        except KeyboardInterrupt:
            # Pager ignores Ctrl-C, so we should too
            pass
