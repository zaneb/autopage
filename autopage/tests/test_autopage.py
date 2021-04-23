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

import sys
import unittest
from unittest import mock

import fixtures

from autopage.tests import sinks

import autopage


class ToTerminalTest(unittest.TestCase):
    def test_pty(self):
        with sinks.TTYFixture() as out:
            ap = autopage.AutoPager(out.stream)
            self.assertTrue(ap.to_terminal())

    def test_stringio(self):
        with sinks.BufferFixture() as out:
            ap = autopage.AutoPager(out.stream)
            self.assertFalse(ap.to_terminal())

    def test_file(self):
        with sinks.TempFixture() as out:
            ap = autopage.AutoPager(out.stream)
            self.assertFalse(ap.to_terminal())

    def test_default_pty(self):
        with sinks.TTYFixture() as out:
            with fixtures.MonkeyPatch('sys.stdout', out.stream):
                ap = autopage.AutoPager()
            self.assertTrue(ap.to_terminal())

    def test_default_file(self):
        with sinks.TempFixture() as out:
            with fixtures.MonkeyPatch('sys.stdout', out.stream):
                ap = autopage.AutoPager()
            self.assertFalse(ap.to_terminal())


class ExitCodeTest(fixtures.TestWithFixtures):
    def setUp(self):
        out = sinks.BufferFixture()
        self.useFixture(out)
        self.ap = autopage.AutoPager(out.stream)

    def test_success(self):
        with self.ap:
            pass
        self.assertEqual(0, self.ap.exit_code())

    def test_broken_pipe(self):
        with self.ap:
            raise BrokenPipeError
        self.assertEqual(141, self.ap.exit_code())

    def test_exception(self):
        class MyException(Exception):
            pass

        def run():
            with self.ap:
                raise MyException

        self.assertRaises(MyException, run)
        self.assertEqual(1, self.ap.exit_code())

    def test_base_exception(self):
        class MyBaseException(BaseException):
            pass

        def run():
            with self.ap:
                raise MyBaseException

        self.assertRaises(MyBaseException, run)
        self.assertEqual(1, self.ap.exit_code())

    def test_interrupt(self):
        def run():
            with self.ap:
                raise KeyboardInterrupt

        self.assertRaises(KeyboardInterrupt, run)
        self.assertEqual(130, self.ap.exit_code())

    def test_system_exit(self):
        def run():
            with self.ap:
                raise SystemExit(42)

        self.assertRaises(SystemExit, run)
        self.assertEqual(42, self.ap.exit_code())


class CleanupTest(unittest.TestCase):
    def test_no_pager_stream_not_closed(self):
        flush = mock.MagicMock()
        with sinks.BufferFixture() as out:
            with autopage.AutoPager(out.stream) as stream:
                stream.flush = flush
                stream.write('foo')
                pass
            self.assertFalse(out.stream.closed)
        flush.assert_called_once()

    def test_no_pager_broken_pipe(self):
        flush = mock.MagicMock(side_effect=BrokenPipeError)
        with sinks.BufferFixture() as out:
            with autopage.AutoPager(out.stream) as stream:
                stream.flush = flush
                stream.write('foo')
                pass
            self.assertTrue(out.stream.closed)
        flush.assert_called_once()

    def test_no_pager_stream_closed(self):
        with sinks.BufferFixture() as out:
            with autopage.AutoPager(out.stream) as stream:
                stream.write('foo')
                stream.close()
                # Calling flush() on a closed stream raises an exception for
                # real streams (but not for StringIO).
                stream.flush = mock.MagicMock(side_effect=ValueError)
            self.assertTrue(out.stream.closed)


class StreamConfigureTest(fixtures.TestWithFixtures):
    def setUp(self):
        out = sinks.TempFixture()
        self.useFixture(out)
        self.stream = out.stream
        self.default_lb = self.stream.line_buffering
        self.default_errors = self.stream.errors
        self.encoding = self.stream.encoding

    def test_line_buffering_on(self):
        ap = autopage.AutoPager(self.stream, line_buffering=True)
        ap._reconfigure_output_stream()
        self.addCleanup(ap._out.close)
        self.assertTrue(ap._out.line_buffering)
        self.assertEqual(self.default_errors, ap._out.errors)
        self.assertEqual(self.encoding, ap._out.encoding)
        self.assertIs(True, ap._line_buffering())
        self.assertEqual(self.default_errors, ap._errors())

    def test_line_buffering_off(self):
        ap = autopage.AutoPager(self.stream, line_buffering=False)
        ap._reconfigure_output_stream()
        self.addCleanup(ap._out.close)
        self.assertFalse(ap._out.line_buffering)
        self.assertEqual(self.default_errors, ap._out.errors)
        self.assertEqual(self.encoding, ap._out.encoding)
        self.assertIs(False, ap._line_buffering())
        self.assertEqual(self.default_errors, ap._errors())

    def test_stdout_line_buffering_on(self):
        with fixtures.MonkeyPatch('sys.stdout', self.stream):
            ap = autopage.AutoPager(line_buffering=True)
            ap._reconfigure_output_stream()
            self.addCleanup(ap._out.close)
            self.assertTrue(sys.stdout.line_buffering)
            self.assertEqual(self.default_errors, sys.stdout.errors)
            self.assertEqual(self.encoding, sys.stdout.encoding)

    @unittest.skip
    def test_errors(self):
        ap = autopage.AutoPager(self.stream,
                                errors=autopage.ErrorStrategy.NAME_REPLACE)
        ap._reconfigure_output_stream()
        self.addCleanup(ap._out.close)
        self.assertEqual(self.default_lb, ap._out.line_buffering)
        self.assertEqual('namereplace', ap._out.errors)
        self.assertNotEqual(self.default_errors, ap._out.errors)
        self.assertEqual(self.encoding, ap._out.encoding)
        self.assertEqual('namereplace', ap._errors())
        self.assertEqual(self.default_lb, ap._line_buffering())

    @unittest.skip
    def test_line_buffering_on_errors(self):
        ap = autopage.AutoPager(self.stream,
                                line_buffering=True,
                                errors=autopage.ErrorStrategy.NAME_REPLACE)
        ap._reconfigure_output_stream()
        self.addCleanup(ap._out.close)
        self.assertTrue(ap._out.line_buffering)
        self.assertEqual('namereplace', ap._out.errors)
        self.assertNotEqual(self.default_errors, ap._out.errors)
        self.assertEqual(self.encoding, ap._out.encoding)
        self.assertIs(True, ap._line_buffering())
        self.assertEqual('namereplace', ap._errors())
