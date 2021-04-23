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

import unittest

from autopage.tests import sinks

import autopage


class ToTerminalTest(unittest.TestCase):
    def test_pty(self):
        with sinks.tty() as out:
            p = autopage.AutoPager(out)
            self.assertTrue(p.to_terminal())

    def test_stringio(self):
        with sinks.buffer() as out:
            p = autopage.AutoPager(out)
            self.assertFalse(p.to_terminal())

    def test_file(self):
        with sinks.temp() as out:
            p = autopage.AutoPager(out)
            self.assertFalse(p.to_terminal())
