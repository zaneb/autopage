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


class ConfigTest(unittest.TestCase):
    def setUp(self):
        class TestCommand(command.PagerCommand):
            def __init__(self):
                self.config = None

            def command(self):
                return []

            def environment_variables(self, config):
                self.config = config
                return None

        self.test_command = TestCommand()

    def _get_ap_config(self, **args):
        ap = autopage.AutoPager(pager_command=self.test_command, **args)
        ap._pager_env()
        return self.test_command.config

    def test_defaults(self):
        config = self._get_ap_config()
        self.assertTrue(config.color)
        self.assertFalse(config.line_buffering_requested)
        self.assertFalse(config.reset_terminal)

    def test_nocolor(self):
        config = self._get_ap_config(allow_color=False)
        self.assertFalse(config.color)
        self.assertFalse(config.line_buffering_requested)
        self.assertFalse(config.reset_terminal)

    def test_reset(self):
        config = self._get_ap_config(reset_on_exit=True)
        self.assertTrue(config.color)
        self.assertFalse(config.line_buffering_requested)
        self.assertTrue(config.reset_terminal)

    def test_linebuffered(self):
        config = self._get_ap_config(line_buffering=True)
        self.assertTrue(config.color)
        self.assertTrue(config.line_buffering_requested)
        self.assertFalse(config.reset_terminal)

    def test_not_linebuffered(self):
        config = self._get_ap_config(line_buffering=False)
        self.assertTrue(config.color)
        self.assertFalse(config.line_buffering_requested)
        self.assertFalse(config.reset_terminal)


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
        self.assertIsNone(env)

    def test_env_none(self):
        cmd = self.TestCommand(None)
        ap = autopage.AutoPager(pager_command=cmd)
        with fixtures.EnvironmentVariable('BAZ', 'quux'):
            env = ap._pager_env()
        self.assertIsNone(env)
