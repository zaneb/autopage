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
import os
import unittest

from autopage.tests import isolation

import autopage


MAX_LINES_PER_PAGE = isolation.LINES - 1


def finite(num_lines):
    def finite():
        ap = autopage.AutoPager()
        with ap as out:
            for i in range(num_lines):
                print(i, file=out)
        return ap.exit_code()
    return finite


def infinite():
    ap = autopage.AutoPager()
    try:
        with ap as out:
            for i in itertools.count():
                print(i, file=out)
    except KeyboardInterrupt:
        pass
    return ap.exit_code()


class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        os.environ['LESS_IS_MORE'] = '1'

    def test_page_to_end(self):
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
        self.assertEqual(0, env.exit_code())

    def test_page_to_middle(self):
        num_lines = 100
        with isolation.isolate(finite(num_lines)) as env:
            pager = isolation.PagerControl(env)

            self.assertEqual(MAX_LINES_PER_PAGE, pager.advance())
            self.assertEqual(MAX_LINES_PER_PAGE, pager.advance())
            self.assertEqual(MAX_LINES_PER_PAGE, pager.quit())
        self.assertEqual(0, env.exit_code())

    def test_exit_pager_early(self):
        with isolation.isolate(infinite) as env:
            pager = isolation.PagerControl(env)

            self.assertEqual(MAX_LINES_PER_PAGE, pager.advance())
            self.assertEqual(MAX_LINES_PER_PAGE, pager.quit())
        self.assertEqual(141, env.exit_code())

    def test_interrupt_early(self):
        with isolation.isolate(infinite) as env:
            pager = isolation.PagerControl(env)

            self.assertEqual(MAX_LINES_PER_PAGE, pager.advance())
            env.interrupt()
            while pager.advance():
                continue
            pager.quit()
            self.assertGreater(pager.total_lines(), MAX_LINES_PER_PAGE)
        self.assertEqual(130, env.exit_code())

    def test_interrupt_early_quit(self):
        with isolation.isolate(infinite) as env:
            pager = isolation.PagerControl(env)

            self.assertEqual(MAX_LINES_PER_PAGE, pager.advance())
            env.interrupt()
            pager.quit()
            self.assertGreater(pager.total_lines(), MAX_LINES_PER_PAGE)
        self.assertEqual(130, env.exit_code())

    def test_interrupt_after_complete(self):
        num_lines = 100
        with isolation.isolate(finite(num_lines)) as env:
            pager = isolation.PagerControl(env)

            while pager.advance():
                continue

            self.assertEqual(num_lines, pager.total_lines())

            for i in range(100):
                env.interrupt()

            self.assertEqual(0, pager.quit())
        self.assertEqual(0, env.exit_code())
