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

import autopage


class EnvironmentTest(unittest.TestCase):
    def test_less_defaults(self):
        ap = autopage.AutoPager()
        less_env = ap._pager_env()['LESS']
        self.assertEqual('RF', less_env)

    def test_less_nocolour(self):
        ap = autopage.AutoPager(allow_color=False)
        less_env = ap._pager_env()['LESS']
        self.assertEqual('F', less_env)

    def test_less_linebuffered(self):
        ap = autopage.AutoPager(line_buffering=True)
        less_env = ap._pager_env()['LESS']
        self.assertEqual('R', less_env)

    def test_less_linebuffered_no_color(self):
        ap = autopage.AutoPager(line_buffering=True, allow_color=False)
        self.assertIsNone(ap._pager_env())

    def test_less_user_override(self):
        ap = autopage.AutoPager()
        with fixtures.EnvironmentVariable('LESS', 'abc'):
            env = ap._pager_env()
        self.assertIsNone(env)
