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

import fixtures  # type: ignore

from typing import Any, Optional, Dict, List

import autopage
from autopage import command


_PagerConfig = command.PagerConfig


class ConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        class TestCommand(command.PagerCommand):
            def __init__(self) -> None:
                self.config: Optional[_PagerConfig] = None

            def command(self) -> List[str]:
                return []

            def environment_variables(
                    self,
                    config: _PagerConfig) -> Optional[Dict[str, str]]:
                self.config = config
                return None

        self.test_command = TestCommand()

    def _get_ap_config(self, **args: Any) -> command.PagerConfig:
        ap = autopage.AutoPager(pager_command=self.test_command, **args)
        ap._pager_env()
        config = self.test_command.config
        assert config is not None
        return config

    def test_defaults(self) -> None:
        config = self._get_ap_config()
        self.assertTrue(config.color)
        self.assertFalse(config.line_buffering_requested)
        self.assertFalse(config.reset_terminal)

    def test_nocolor(self) -> None:
        config = self._get_ap_config(allow_color=False)
        self.assertFalse(config.color)
        self.assertFalse(config.line_buffering_requested)
        self.assertFalse(config.reset_terminal)

    def test_reset(self) -> None:
        config = self._get_ap_config(reset_on_exit=True)
        self.assertTrue(config.color)
        self.assertFalse(config.line_buffering_requested)
        self.assertTrue(config.reset_terminal)

    def test_linebuffered(self) -> None:
        config = self._get_ap_config(line_buffering=True)
        self.assertTrue(config.color)
        self.assertTrue(config.line_buffering_requested)
        self.assertFalse(config.reset_terminal)

    def test_not_linebuffered(self) -> None:
        config = self._get_ap_config(line_buffering=False)
        self.assertTrue(config.color)
        self.assertFalse(config.line_buffering_requested)
        self.assertFalse(config.reset_terminal)


class EnvironmentBuildTest(unittest.TestCase):
    class TestCommand(command.PagerCommand):
        def __init__(self, env: Optional[Dict[str, str]]):
            self._env = env

        def command(self) -> List[str]:
            return ['foo']

        def environment_variables(self,
                                  config: _PagerConfig) -> Optional[Dict[str,
                                                                         str]]:
            return self._env

    def test_env(self) -> None:
        cmd = self.TestCommand({"FOO": "bar"})
        ap = autopage.AutoPager(pager_command=cmd)
        with fixtures.EnvironmentVariable('BAZ', 'quux'):
            env = ap._pager_env()
        self.assertIsNotNone(env)
        assert env is not None
        self.assertEqual('quux', env['BAZ'])
        self.assertEqual('bar', env['FOO'])

    def test_env_empty(self) -> None:
        cmd = self.TestCommand({})
        ap = autopage.AutoPager(pager_command=cmd)
        with fixtures.EnvironmentVariable('BAZ', 'quux'):
            env = ap._pager_env()
        self.assertIsNone(env)

    def test_env_none(self) -> None:
        cmd = self.TestCommand(None)
        ap = autopage.AutoPager(pager_command=cmd)
        with fixtures.EnvironmentVariable('BAZ', 'quux'):
            env = ap._pager_env()
        self.assertIsNone(env)
