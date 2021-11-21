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

import subprocess
import sys
import unittest
from unittest import mock

import fixtures  # type: ignore

from typing import Optional, List, Dict

from autopage.tests import sinks

import autopage
from autopage import command


_PagerConfig = command.PagerConfig


class PagedStreamTest(fixtures.TestWithFixtures):
    def setUp(self) -> None:
        out = sinks.TTYFixture()
        self.useFixture(out)
        self.stream = out.stream
        self.useFixture(fixtures.MonkeyPatch('sys.stdout', self.stream))
        popen = fixtures.MockPatch('subprocess.Popen')
        self.useFixture(popen)
        self.popen = popen.mock

    def test_defaults(self) -> None:
        class TestCommand(command.PagerCommand):
            def command(self) -> List[str]:
                return []

            def environment_variables(
                    self,
                    config: _PagerConfig) -> Optional[Dict[str, str]]:
                return None

        tc = TestCommand()
        ap = autopage.AutoPager(pager_command=tc, line_buffering=False)
        with mock.patch.object(ap, '_pager_env') as get_env, \
                mock.patch.object(tc, 'command') as cmd:
            stream = ap._paged_stream()
            self.popen.assert_called_once_with(
                cmd.return_value,
                env=get_env.return_value,
                bufsize=-1,
                universal_newlines=True,
                encoding='UTF-8',
                errors='strict',
                stdin=subprocess.PIPE,
                stdout=None)
            self.assertIs(stream, self.popen.return_value.stdin)

    def test_defaults_cmd_as_class(self) -> None:
        class TestCommand(command.PagerCommand):
            def command(self) -> List[str]:
                return []

            def environment_variables(
                    self,
                    config: _PagerConfig) -> Optional[Dict[str, str]]:
                return None

        with mock.patch.object(TestCommand, 'command') as cmd:
            ap = autopage.AutoPager(pager_command=TestCommand,
                                    line_buffering=False)
            with mock.patch.object(ap, '_pager_env') as get_env:
                stream = ap._paged_stream()
                self.popen.assert_called_once_with(
                    cmd.return_value,
                    env=get_env.return_value,
                    bufsize=-1,
                    universal_newlines=True,
                    encoding='UTF-8',
                    errors='strict',
                    stdin=subprocess.PIPE,
                    stdout=None)
                self.assertIs(stream, self.popen.return_value.stdin)

    def test_defaults_cmd_as_string(self) -> None:
        ap = autopage.AutoPager(pager_command='foo bar',
                                line_buffering=False)
        with mock.patch.object(ap, '_pager_env') as get_env:
            stream = ap._paged_stream()
            self.popen.assert_called_once_with(
                ['foo', 'bar'],
                env=get_env.return_value,
                bufsize=-1,
                universal_newlines=True,
                encoding='UTF-8',
                errors='strict',
                stdin=subprocess.PIPE,
                stdout=None)
            self.assertIs(stream, self.popen.return_value.stdin)

    def test_defaults_cmd_as_int(self) -> None:
        self.assertRaises(TypeError, autopage.AutoPager,
                          pager_command=42)

    def test_line_buffering(self) -> None:
        ap = autopage.AutoPager(line_buffering=True)
        stream = ap._paged_stream()
        self.popen.assert_called_once_with(
            mock.ANY,
            env=mock.ANY,
            bufsize=1,
            universal_newlines=True,
            encoding=mock.ANY,
            errors=mock.ANY,
            stdin=subprocess.PIPE,
            stdout=None)
        self.assertIs(stream, self.popen.return_value.stdin)

    def test_errors(self) -> None:
        ap = autopage.AutoPager(errors=autopage.ErrorStrategy.NAME_REPLACE)
        stream = ap._paged_stream()
        self.popen.assert_called_once_with(
            mock.ANY,
            env=mock.ANY,
            bufsize=mock.ANY,
            universal_newlines=mock.ANY,
            encoding=mock.ANY,
            errors='namereplace',
            stdin=subprocess.PIPE,
            stdout=None)
        self.assertIs(stream, self.popen.return_value.stdin)

    def test_explicit_stdout_stream(self) -> None:
        ap = autopage.AutoPager(self.stream)
        stream = ap._paged_stream()
        self.popen.assert_called_once_with(
            mock.ANY,
            env=mock.ANY,
            bufsize=mock.ANY,
            universal_newlines=mock.ANY,
            encoding=mock.ANY,
            errors=mock.ANY,
            stdin=subprocess.PIPE,
            stdout=None)
        self.assertIs(stream, self.popen.return_value.stdin)

    def test_explicit_stream(self) -> None:
        with sinks.TTYFixture() as tty:
            ap = autopage.AutoPager(tty.stream)
            stream = ap._paged_stream()
            self.popen.assert_called_once_with(
                mock.ANY,
                env=mock.ANY,
                bufsize=mock.ANY,
                universal_newlines=mock.ANY,
                encoding=mock.ANY,
                errors=mock.ANY,
                stdin=subprocess.PIPE,
                stdout=tty.stream)
            self.assertIs(stream, self.popen.return_value.stdin)


class ToTerminalTest(unittest.TestCase):
    def test_pty(self) -> None:
        with sinks.TTYFixture() as out:
            ap = autopage.AutoPager(out.stream)
            self.assertTrue(ap.to_terminal())

    def test_stringio(self) -> None:
        with sinks.BufferFixture() as out:
            ap = autopage.AutoPager(out.stream)
            self.assertFalse(ap.to_terminal())

    def test_file(self) -> None:
        with sinks.TempFixture() as out:
            ap = autopage.AutoPager(out.stream)
            self.assertFalse(ap.to_terminal())

    def test_default_pty(self) -> None:
        with sinks.TTYFixture() as out:
            with fixtures.MonkeyPatch('sys.stdout', out.stream):
                ap = autopage.AutoPager()
            self.assertTrue(ap.to_terminal())

    def test_default_file(self) -> None:
        with sinks.TempFixture() as out:
            with fixtures.MonkeyPatch('sys.stdout', out.stream):
                ap = autopage.AutoPager()
            self.assertFalse(ap.to_terminal())

    def test_launch_pager(self) -> None:
        ap = autopage.AutoPager()
        with mock.patch.object(ap, 'to_terminal', return_value=True), \
                mock.patch.object(ap, '_paged_stream') as page, \
                mock.patch.object(ap, '_reconfigure_output_stream') as reconf:
            with ap as stream:
                page.assert_called_once()
                self.assertIs(page.return_value, stream)
                reconf.assert_not_called()

    def test_launch_pager_fail(self) -> None:
        outstream = mock.Mock()
        ap = autopage.AutoPager(outstream)
        with mock.patch.object(ap, 'to_terminal', return_value=True), \
                mock.patch.object(ap, '_paged_stream',
                                  side_effect=OSError) as page, \
                mock.patch.object(ap, '_reconfigure_output_stream') as reconf:
            with ap as stream:
                page.assert_called_once()
                reconf.assert_called_once()
                self.assertIs(outstream, stream)

    def test_no_pager(self) -> None:
        outstream = mock.Mock()
        ap = autopage.AutoPager(outstream)
        with mock.patch.object(ap, 'to_terminal', return_value=False), \
                mock.patch.object(ap, '_paged_stream') as page, \
                mock.patch.object(ap, '_reconfigure_output_stream') as reconf:
            with ap as stream:
                page.assert_not_called()
                self.assertIs(outstream, stream)
                reconf.assert_called_once()

    def test_pager_cat(self) -> None:
        outstream = mock.Mock()
        cat = command.CustomPager('cat')
        ap = autopage.AutoPager(outstream, pager_command=cat)
        with mock.patch.object(ap, 'to_terminal', return_value=True), \
                mock.patch.object(ap, '_paged_stream') as page, \
                mock.patch.object(ap, '_reconfigure_output_stream') as reconf:
            with ap as stream:
                page.assert_not_called()
                self.assertIs(outstream, stream)
                reconf.assert_called_once()


class ExitCodeTest(fixtures.TestWithFixtures):
    def setUp(self) -> None:
        out = sinks.BufferFixture()
        self.useFixture(out)
        self.ap = autopage.AutoPager(out.stream)

    def test_success(self) -> None:
        with self.ap:
            pass
        self.assertEqual(0, self.ap.exit_code())

    def test_pager_broken_pipe_flush(self) -> None:
        flush = mock.MagicMock(side_effect=BrokenPipeError)
        with sinks.TTYFixture() as out:
            ap = autopage.AutoPager(out.stream)
            with fixtures.MockPatch('subprocess.Popen') as popen:
                with sinks.BufferFixture() as pager_in:
                    popen.mock.return_value.stdin = pager_in.stream
                    with ap as stream:
                        stream.write('foo')
                        stream.close = flush  # type: ignore
            self.assertEqual(141, ap.exit_code())

    def test_no_pager_broken_pipe_flush(self) -> None:
        flush = mock.MagicMock(side_effect=BrokenPipeError)
        with self.ap as stream:
            stream.write('foo')
            stream.flush = flush  # type: ignore
        self.assertEqual(141, self.ap.exit_code())

    def test_broken_pipe(self) -> None:
        with self.ap:
            raise BrokenPipeError
        self.assertEqual(141, self.ap.exit_code())

    def test_exception(self) -> None:
        class MyException(Exception):
            pass

        def run() -> None:
            with self.ap:
                raise MyException

        self.assertRaises(MyException, run)
        self.assertEqual(1, self.ap.exit_code())

    def test_base_exception(self) -> None:
        class MyBaseException(BaseException):
            pass

        def run() -> None:
            with self.ap:
                raise MyBaseException

        self.assertRaises(MyBaseException, run)
        self.assertEqual(1, self.ap.exit_code())

    def test_interrupt(self) -> None:
        def run() -> None:
            with self.ap:
                raise KeyboardInterrupt

        self.assertRaises(KeyboardInterrupt, run)
        self.assertEqual(130, self.ap.exit_code())

    def test_system_exit(self) -> None:
        def run() -> None:
            with self.ap:
                raise SystemExit(42)

        self.assertRaises(SystemExit, run)
        self.assertEqual(42, self.ap.exit_code())


class CleanupTest(unittest.TestCase):
    def test_no_pager_stream_not_closed(self) -> None:
        flush = mock.MagicMock()
        with sinks.BufferFixture() as out:
            with autopage.AutoPager(out.stream) as stream:
                stream.flush = flush  # type: ignore
                stream.write('foo')
            self.assertFalse(out.stream.closed)
        flush.assert_called_once()

    def test_no_pager_broken_pipe(self) -> None:
        flush = mock.MagicMock(side_effect=BrokenPipeError)
        with sinks.BufferFixture() as out:
            with autopage.AutoPager(out.stream) as stream:
                stream.flush = flush  # type: ignore
                stream.write('foo')
            self.assertTrue(out.stream.closed)
        flush.assert_called_once()

    def test_no_pager_broken_pipe_flush(self) -> None:
        flush = mock.MagicMock(side_effect=BrokenPipeError)
        with sinks.BufferFixture() as out:
            with autopage.AutoPager(out.stream) as stream:
                stream.write('foo')
                stream.flush = flush  # type: ignore
            self.assertTrue(out.stream.closed)
        flush.assert_called_once()

    def test_no_pager_stream_closed(self) -> None:
        flush = mock.MagicMock(side_effect=ValueError)
        with sinks.BufferFixture() as out:
            with autopage.AutoPager(out.stream) as stream:
                stream.write('foo')
                stream.close()
                # Calling flush() on a closed stream raises an exception for
                # real streams (but not for StringIO).
                stream.flush = flush  # type: ignore
            self.assertTrue(out.stream.closed)

    def test_pager_stream_not_closed(self) -> None:
        with sinks.TTYFixture() as out:
            ap = autopage.AutoPager(out.stream)
            with fixtures.MockPatch('subprocess.Popen') as popen:
                with sinks.BufferFixture() as pager_in:
                    popen.mock.return_value.stdin = pager_in.stream
                    with ap as stream:
                        self.assertIs(pager_in.stream, stream)
                    self.assertTrue(pager_in.stream.closed)

    def test_pager_stream_not_closed_interrupt(self) -> None:
        with sinks.TTYFixture() as out:
            ap = autopage.AutoPager(out.stream)
            with fixtures.MockPatch('subprocess.Popen') as popen:
                with sinks.BufferFixture() as pager_in:
                    popen.mock.return_value.stdin = pager_in.stream

                    def run() -> None:
                        with ap as stream:
                            self.assertIs(pager_in.stream, stream)
                            raise KeyboardInterrupt

                    self.assertRaises(KeyboardInterrupt, run)
                    self.assertTrue(pager_in.stream.closed)

    def test_pager_broken_pipe(self) -> None:
        flush = mock.MagicMock(side_effect=BrokenPipeError)
        with sinks.TTYFixture() as out:
            ap = autopage.AutoPager(out.stream)
            with fixtures.MockPatch('subprocess.Popen') as popen:
                with sinks.BufferFixture() as pager_in:
                    popen.mock.return_value.stdin = pager_in.stream
                    pager_in.stream.flush = flush
                    with ap as stream:
                        self.assertIs(pager_in.stream, stream)
                    self.assertTrue(pager_in.stream.closed)
                    popen.mock.return_value.wait.assert_called_once()

    def test_pager_stream_closed(self) -> None:
        with sinks.TTYFixture() as out:
            ap = autopage.AutoPager(out.stream)
            with fixtures.MockPatch('subprocess.Popen') as popen:
                with sinks.BufferFixture() as pager_in:
                    popen.mock.return_value.stdin = pager_in.stream
                    with ap as stream:
                        self.assertIs(pager_in.stream, stream)
                        stream.close()
                    popen.mock.return_value.wait.assert_called_once()


class StreamConfigureTest(fixtures.TestWithFixtures):
    def setUp(self) -> None:
        out = sinks.TempFixture()
        self.useFixture(out)
        self.stream = out.stream
        self.default_lb = self.stream.line_buffering
        self.default_errors = self.stream.errors
        self.encoding = self.stream.encoding

    def test_line_buffering_on(self) -> None:
        ap = autopage.AutoPager(self.stream, line_buffering=True)
        ap._reconfigure_output_stream()
        self.addCleanup(ap._out.close)
        self.assertTrue(ap._out.line_buffering)
        self.assertEqual(self.default_errors, ap._out.errors)
        self.assertEqual(self.encoding, ap._out.encoding)
        self.assertIs(True, ap._line_buffering())
        self.assertEqual(self.default_errors, ap._errors())

    def test_line_buffering_off(self) -> None:
        ap = autopage.AutoPager(self.stream, line_buffering=False)
        ap._reconfigure_output_stream()
        self.addCleanup(ap._out.close)
        self.assertFalse(ap._out.line_buffering)
        self.assertEqual(self.default_errors, ap._out.errors)
        self.assertEqual(self.encoding, ap._out.encoding)
        self.assertIs(False, ap._line_buffering())
        self.assertEqual(self.default_errors, ap._errors())

    def test_stdout_line_buffering_on(self) -> None:
        with fixtures.MonkeyPatch('sys.stdout', self.stream):
            ap = autopage.AutoPager(line_buffering=True)
            ap._reconfigure_output_stream()
            self.addCleanup(ap._out.close)
            self.assertTrue(sys.stdout.line_buffering)
            self.assertEqual(self.default_errors, sys.stdout.errors)
            self.assertEqual(self.encoding, sys.stdout.encoding)

    def test_errors(self) -> None:
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

    def test_errors_string(self) -> None:
        ap = autopage.AutoPager(self.stream,
                                errors='namereplace')  # type: ignore
        ap._reconfigure_output_stream()
        self.addCleanup(ap._out.close)
        self.assertEqual(self.default_lb, ap._out.line_buffering)
        self.assertEqual('namereplace', ap._out.errors)
        self.assertNotEqual(self.default_errors, ap._out.errors)
        self.assertEqual(self.encoding, ap._out.encoding)
        self.assertEqual('namereplace', ap._errors())
        self.assertEqual(self.default_lb, ap._line_buffering())

    def test_errors_bogus_string(self) -> None:
        self.assertRaises(ValueError,
                          autopage.AutoPager,
                          self.stream, errors='panic')

    def test_line_buffering_on_errors(self) -> None:
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
