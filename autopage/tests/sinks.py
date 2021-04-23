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

import io
import os
import pty
import tempfile

import fixtures


class TTYFixture(fixtures.Fixture):
    def _setUp(self):
        self._k, term = pty.openpty()
        self.stream = os.fdopen(term, 'w')
        self.addCleanup(self.stream.close)
        self.addCleanup(os.close, self._k)


class TempFixture(fixtures.Fixture):
    def __init__(self, nativeio=True):
        self._nativeio = nativeio

    def _setUp(self):
        self.stream = tempfile.TemporaryFile('w')

        def close():
            try:
                self.stream.close()
            except ValueError:
                pass

        self.addCleanup(close)


class BufferFixture(fixtures.Fixture):
    def _setUp(self):
        self.stream = io.StringIO()
        self.addCleanup(self.stream.close)
