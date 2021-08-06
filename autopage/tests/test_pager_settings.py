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
from autopage import command


class CommandTest(unittest.TestCase):
    def test_cmd_default(self):
        with fixtures.EnvironmentVariable('PAGER'):
            def_cmd = command.DefaultPager()
        ap = autopage.AutoPager(pager_command=def_cmd)
        self.assertListEqual(['less'], ap._pager_cmd())

    def test_cmd_override(self):
        with fixtures.EnvironmentVariable('PAGER', 'less "-r" +F'):
            def_cmd = command.DefaultPager()
        ap = autopage.AutoPager(pager_command=def_cmd)
        cmd = ap._pager_cmd()
        self.assertListEqual(['less', '-r', '+F'], cmd)


class EnvironmentTest(unittest.TestCase):
    def test_less_defaults(self):
        ap = autopage.AutoPager(pager_command=command.Less())
        less_env = ap._pager_env()['LESS']
        self.assertEqual('RFX', less_env)

    def test_less_nocolour(self):
        ap = autopage.AutoPager(pager_command=command.Less(),
                                allow_color=False)
        less_env = ap._pager_env()['LESS']
        self.assertEqual('FX', less_env)

    def test_less_reset(self):
        ap = autopage.AutoPager(pager_command=command.Less(),
                                reset_on_exit=True)
        less_env = ap._pager_env()['LESS']
        self.assertEqual('R', less_env)

    def test_less_linebuffered(self):
        ap = autopage.AutoPager(pager_command=command.Less(),
                                line_buffering=True)
        less_env = ap._pager_env()['LESS']
        self.assertEqual('RX', less_env)

    def test_less_linebuffered_reset(self):
        ap = autopage.AutoPager(pager_command=command.Less(),
                                line_buffering=True,
                                reset_on_exit=True)
        less_env = ap._pager_env()['LESS']
        self.assertEqual('R', less_env)

    def test_less_linebuffered_nocolor(self):
        ap = autopage.AutoPager(pager_command=command.Less(),
                                line_buffering=True,
                                allow_color=False)
        less_env = ap._pager_env()['LESS']
        self.assertEqual('X', less_env)

    def test_less_linebuffered_nocolor_reset(self):
        ap = autopage.AutoPager(pager_command=command.Less(),
                                line_buffering=True,
                                allow_color=False,
                                reset_on_exit=True)
        self.assertNotIn('LESS', ap._pager_env())

    def test_less_user_override(self):
        ap = autopage.AutoPager(pager_command=command.Less())
        with fixtures.EnvironmentVariable('LESS', 'abc'):
            env = ap._pager_env()
        self.assertEqual('abc', env['LESS'])

    def test_lv_defaults(self):
        ap = autopage.AutoPager(pager_command=command.LV())
        lv_env = ap._pager_env()['LV']
        self.assertEqual('-c', lv_env)

    def test_lv_nocolour(self):
        ap = autopage.AutoPager(pager_command=command.LV(),
                                allow_color=False)
        self.assertNotIn('LV', ap._pager_env())

    def test_lv_user_override(self):
        ap = autopage.AutoPager(pager_command=command.LV())
        with fixtures.EnvironmentVariable('LV', 'abc'):
            env = ap._pager_env()
        self.assertEqual('abc', env['LV'])


class EnvironmentBuildTest(unittest.TestCase):
    class TestCommand(command.PagerCommand):
        def __init__(self, env):
            self._env = env

        def command(self):
            return ['foo']

        def environment_variables(self, config):
            return self._env

    def test_env(self):
        cmd = self.TestCommand({"FOO": "bar"})
        ap = autopage.AutoPager(pager_command=cmd)
        with fixtures.EnvironmentVariable('BAZ', 'quux'):
            env = ap._pager_env()
        self.assertEqual('quux', env['BAZ'])
        self.assertEqual('bar', env['FOO'])

    def test_env_empty(self):
        cmd = self.TestCommand({})
        ap = autopage.AutoPager(pager_command=cmd)
        with fixtures.EnvironmentVariable('BAZ', 'quux'):
            env = ap._pager_env()
        self.assertEqual('quux', env['BAZ'])

    def test_env_none(self):
        cmd = self.TestCommand(None)
        ap = autopage.AutoPager(pager_command=cmd)
        with fixtures.EnvironmentVariable('BAZ', 'quux'):
            env = ap._pager_env()
        self.assertEqual('quux', env['BAZ'])
