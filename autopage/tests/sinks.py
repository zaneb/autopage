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
import io
import os
import pty
import tempfile


@contextlib.contextmanager
def tty():
    k, term = pty.openpty()
    try:
        with os.fdopen(term, 'w') as stream:
            yield stream
    finally:
        os.close(k)


@contextlib.contextmanager
def temp():
    with tempfile.TemporaryFile('w') as temp:
        yield temp


@contextlib.contextmanager
def buffer():
    with contextlib.closing(io.StringIO()) as buf:
        yield buf
