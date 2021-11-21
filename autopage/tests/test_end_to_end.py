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

import itertools
import unittest
import sys

from autopage.tests import isolation

import typing

import autopage


MAX_LINES_PER_PAGE = isolation.LINES - 1


class finite:
    def __init__(self, num_lines: int, **kwargs: typing.Any):
        self.num_lines = num_lines
        self.kwargs = kwargs

    def __call__(self) -> int:
        ap = autopage.AutoPager(pager_command=autopage.command.Less(),
                                **self.kwargs)
        with ap as out:
            for i in range(self.num_lines):
                print(i, file=out)
        return ap.exit_code()


def infinite() -> int:
    ap = autopage.AutoPager(pager_command=autopage.command.Less())
    try:
        with ap as out:
            for i in itertools.count():
                print(i, file=out)
    except KeyboardInterrupt:
        pass
    return ap.exit_code()


def from_stdin() -> int:
    ap = autopage.AutoPager(pager_command=autopage.command.Less(),
                            line_buffering=autopage.line_buffer_from_input())
    with ap as out:
        try:
            for line in sys.stdin:
                print(line.rstrip(), file=out)
        except KeyboardInterrupt:
            pass
    return ap.exit_code()


def with_exception() -> int:
    class MyException(Exception):
        pass

    ap = autopage.AutoPager(pager_command=autopage.command.Less())
    try:
        with ap as out:
            for i in range(50):
                print(i, file=out)
            raise MyException()
    except MyException:
        pass
    return ap.exit_code()


def with_stderr_output() -> int:
    ap = autopage.AutoPager(pager_command=autopage.command.Less())
    with ap as out:
        for i in range(50):
            print(i, file=out)
    print("Hello world", file=sys.stderr)
    return ap.exit_code()


class InvokePagerTest(unittest.TestCase):
    def test_page_to_end(self) -> None:
        num_lines = 100
        with isolation.isolate(finite(num_lines)) as env:
            pager = isolation.PagerControl(env)

            lines = num_lines
            while lines > 0:
                expected = min(lines, MAX_LINES_PER_PAGE)
                self.assertEqual(expected, pager.advance())
                lines -= expected
            self.assertEqual(0, pager.advance())
            self.assertEqual(0, pager.advance())
            self.assertEqual(0, pager.quit())

            self.assertEqual(num_lines, pager.total_lines())
            self.assertFalse(env.error_output())
        self.assertEqual(0, env.exit_code())

    def test_page_to_middle(self) -> None:
        num_lines = 100
        with isolation.isolate(finite(num_lines)) as env:
            pager = isolation.PagerControl(env)

            self.assertEqual(MAX_LINES_PER_PAGE, pager.advance())
            self.assertEqual(MAX_LINES_PER_PAGE, pager.advance())
            self.assertEqual(MAX_LINES_PER_PAGE, pager.quit())
            self.assertFalse(env.error_output())
        self.assertEqual(0, env.exit_code())

    def test_exit_pager_early(self) -> None:
        with isolation.isolate(infinite) as env:
            pager = isolation.PagerControl(env)

            self.assertEqual(MAX_LINES_PER_PAGE, pager.advance())
            self.assertEqual(MAX_LINES_PER_PAGE, pager.quit())
            self.assertFalse(env.error_output())
        self.assertEqual(141, env.exit_code())

    def test_interrupt_early(self) -> None:
        with isolation.isolate(infinite) as env:
            pager = isolation.PagerControl(env)

            self.assertEqual(MAX_LINES_PER_PAGE, pager.advance())
            env.interrupt()
            while pager.advance():
                continue
            pager.quit()
            self.assertGreater(pager.total_lines(), MAX_LINES_PER_PAGE)
            self.assertFalse(env.error_output())
        self.assertEqual(130, env.exit_code())

    def test_interrupt_early_quit(self) -> None:
        with isolation.isolate(infinite) as env:
            pager = isolation.PagerControl(env)

            self.assertEqual(MAX_LINES_PER_PAGE, pager.advance())
            env.interrupt()
            pager.quit()
            self.assertGreater(pager.total_lines(), MAX_LINES_PER_PAGE)
            self.assertFalse(env.error_output())
        self.assertEqual(130, env.exit_code())

    def test_interrupt_in_middle_after_complete(self) -> None:
        num_lines = 100
        with isolation.isolate(finite(num_lines)) as env:
            pager = isolation.PagerControl(env)

            self.assertEqual(MAX_LINES_PER_PAGE, pager.advance())

            for i in range(100):
                env.interrupt()

            self.assertEqual(MAX_LINES_PER_PAGE, pager.quit())
            self.assertFalse(env.error_output())
        self.assertEqual(0, env.exit_code())

    def test_interrupt_at_end_after_complete(self) -> None:
        num_lines = 100
        with isolation.isolate(finite(num_lines)) as env:
            pager = isolation.PagerControl(env)

            while pager.advance():
                continue

            self.assertEqual(num_lines, pager.total_lines())

            for i in range(100):
                env.interrupt()

            self.assertEqual(0, pager.quit())
            self.assertFalse(env.error_output())
        self.assertEqual(0, env.exit_code())

    def test_short_output(self) -> None:
        num_lines = 10
        with isolation.isolate(finite(num_lines)) as env:
            pager = isolation.PagerControl(env)

            for i, l in enumerate(pager.read_lines(num_lines)):
                self.assertEqual(str(i), l.rstrip())
            self.assertFalse(env.error_output())
        self.assertEqual(0, env.exit_code())

    def test_short_output_reset(self) -> None:
        num_lines = 10
        with isolation.isolate(finite(num_lines, reset_on_exit=True)) as env:
            pager = isolation.PagerControl(env)

            self.assertEqual(num_lines, pager.quit())
            self.assertFalse(env.error_output())
        self.assertEqual(0, env.exit_code())

    def test_short_streaming_output(self) -> None:
        num_lines = 10
        with isolation.isolate(from_stdin, stdin_pipe=True) as env:
            pager = isolation.PagerControl(env)

            with env.stdin_pipe() as in_pipe:
                for i in range(num_lines):
                    print(i, file=in_pipe)

            for i, l in enumerate(pager.read_lines(num_lines)):
                self.assertEqual(i, int(l))

            env.interrupt()
            self.assertEqual(0, pager.quit())
            self.assertFalse(env.error_output())
        self.assertEqual(0, env.exit_code())

    def test_exception(self) -> None:
        num_lines = 50
        with isolation.isolate(with_exception) as env:
            pager = isolation.PagerControl(env)

            lines = num_lines
            while lines > 0:
                expected = min(lines, MAX_LINES_PER_PAGE)
                self.assertEqual(expected, pager.advance())
                lines -= expected
            self.assertEqual(0, pager.advance())
            self.assertEqual(0, pager.advance())
            self.assertEqual(0, pager.quit())

            self.assertEqual(num_lines, pager.total_lines())
            self.assertFalse(env.error_output())
        self.assertEqual(1, env.exit_code())

    def test_stderr_output(self) -> None:
        num_lines = 50
        with isolation.isolate(with_stderr_output) as env:
            pager = isolation.PagerControl(env)

            lines = num_lines
            while lines > 0:
                expected = min(lines, MAX_LINES_PER_PAGE)
                self.assertEqual(expected, pager.advance())
                lines -= expected
            self.assertEqual(0, pager.advance())
            self.assertEqual(0, pager.advance())
            self.assertEqual(0, pager.quit())

            self.assertEqual(num_lines, pager.total_lines())
            self.assertEqual('Hello world\n', env.error_output())
        self.assertEqual(0, env.exit_code())


class NoPagerTest(unittest.TestCase):
    def test_pipe_output_to_end(self) -> None:
        num_lines = 100
        with isolation.isolate(finite(num_lines),
                               stdout_pipe=True) as env:
            with env.stdout_pipe() as out:
                output = out.readlines()

            self.assertEqual(num_lines, len(output))
            self.assertFalse(env.error_output())
        self.assertEqual(0, env.exit_code())

    def test_exit_early(self) -> None:
        with isolation.isolate(infinite, stdout_pipe=True) as env:
            with env.stdout_pipe() as out:
                for i in range(500):
                    out.readline()
            self.assertFalse(env.error_output())
        self.assertEqual(141, env.exit_code())

    def test_exit_early_buffered(self) -> None:
        num_lines = 10
        with isolation.isolate(from_stdin,
                               stdin_pipe=True, stdout_pipe=True) as env:
            with env.stdin_pipe() as in_pipe:
                for i in range(num_lines):
                    print(i, file=in_pipe)
            with env.stdout_pipe():
                # Close output without reading contents of buffer
                pass
            self.assertFalse(env.error_output())
        self.assertEqual(141, env.exit_code())

    def test_interrupt_early(self) -> None:
        with isolation.isolate(infinite, stdout_pipe=True) as env:
            env.interrupt()
            with env.stdout_pipe() as out:
                output = out.readlines()
            self.assertGreater(len(output), 0)
            self.assertFalse(env.error_output())
        self.assertEqual(130, env.exit_code())

    def test_short_streaming_output(self) -> None:
        num_lines = 10
        with isolation.isolate(from_stdin,
                               stdin_pipe=True, stdout_pipe=True) as env:
            with env.stdin_pipe() as in_pipe:
                for i in range(num_lines):
                    print(i, file=in_pipe)

            with env.stdout_pipe() as out:
                for i in range(num_lines):
                    self.assertEqual(i, int(out.readline()))
                env.interrupt()
                self.assertEqual(0, len(out.readlines()))

            self.assertFalse(env.error_output())
        self.assertEqual(0, env.exit_code())
