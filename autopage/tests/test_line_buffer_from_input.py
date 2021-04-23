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

import fixtures

from autopage.tests import sinks

import autopage


class LineBufferFromInputTest(unittest.TestCase):
    def test_tty(self):
        with sinks.TTYFixture() as inp:
            self.assertTrue(autopage.line_buffer_from_input(inp.stream))

    def test_file(self):
        with sinks.TempFixture() as inp:
            self.assertFalse(autopage.line_buffer_from_input(inp.stream))

    def test_default_tty(self):
        with sinks.TTYFixture() as inp:
            with fixtures.MonkeyPatch('sys.stdin', inp.stream):
                self.assertTrue(autopage.line_buffer_from_input())

    def test_default_file(self):
        with sinks.TempFixture() as inp:
            with fixtures.MonkeyPatch('sys.stdin', inp.stream):
                self.assertFalse(autopage.line_buffer_from_input())
