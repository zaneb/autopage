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
import sys

import fixtures  # type: ignore

import typing

from autopage import command


class MoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.cmd = command.More()

    def test_cmd(self) -> None:
        self.assertEqual(['more'], self.cmd.command())

    def test_less_env_defaults(self) -> None:
        config = command.PagerConfig(color=True,
                                     line_buffering_requested=False,
                                     reset_terminal=False)
        self.assertIsNone(self.cmd.environment_variables(config))


class LessTest(unittest.TestCase):
    def setUp(self) -> None:
        self.cmd: command.PagerCommand = command.Less()

    def _env(self, config: command.PagerConfig) -> typing.Dict:
        return self.cmd.environment_variables(config) or {}

    def test_cmd(self) -> None:
        self.assertEqual(['less'], self.cmd.command())

    def test_less_env_defaults(self) -> None:
        config = command.PagerConfig(color=True,
                                     line_buffering_requested=False,
                                     reset_terminal=False)
        less_env = self._env(config)['LESS']
        self.assertEqual('RFX', less_env)

    def test_less_env_nocolor(self) -> None:
        config = command.PagerConfig(color=False,
                                     line_buffering_requested=False,
                                     reset_terminal=False)
        less_env = self._env(config)['LESS']
        self.assertEqual('FX', less_env)

    def test_less_env_reset(self) -> None:
        config = command.PagerConfig(color=True,
                                     line_buffering_requested=False,
                                     reset_terminal=True)
        less_env = self._env(config)['LESS']
        self.assertEqual('R', less_env)

    def test_less_env_nocolor_reset(self) -> None:
        config = command.PagerConfig(color=False,
                                     line_buffering_requested=False,
                                     reset_terminal=True)
        self.assertNotIn('LESS', self._env(config))

    def test_less_env_linebuffered(self) -> None:
        config = command.PagerConfig(color=True,
                                     line_buffering_requested=True,
                                     reset_terminal=False)
        less_env = self._env(config)['LESS']
        self.assertEqual('RX', less_env)

    def test_less_env_linebuffered_reset(self) -> None:
        config = command.PagerConfig(color=True,
                                     line_buffering_requested=True,
                                     reset_terminal=True)
        less_env = self._env(config)['LESS']
        self.assertEqual('R', less_env)

    def test_less_env_linebuffered_nocolor(self) -> None:
        config = command.PagerConfig(color=False,
                                     line_buffering_requested=True,
                                     reset_terminal=False)
        less_env = self._env(config)['LESS']
        self.assertEqual('X', less_env)

    def test_less_env_linebuffered_nocolor_reset(self) -> None:
        config = command.PagerConfig(color=False,
                                     line_buffering_requested=True,
                                     reset_terminal=True)
        self.assertNotIn('LESS', self._env(config))

    def test_less_env_override(self) -> None:
        config = command.PagerConfig(color=True,
                                     line_buffering_requested=False,
                                     reset_terminal=False)
        with fixtures.EnvironmentVariable('LESS', 'abc'):
            env = self._env(config)
        self.assertNotIn('LESS', env)


class LVTest(unittest.TestCase):
    def setUp(self) -> None:
        self.cmd: command.PagerCommand = command.LV()

    def _env(self, config: command.PagerConfig) -> typing.Dict:
        return self.cmd.environment_variables(config) or {}

    def test_cmd(self) -> None:
        self.assertEqual(['lv'], self.cmd.command())

    def test_lv_env_defaults(self) -> None:
        config = command.PagerConfig(color=True,
                                     line_buffering_requested=False,
                                     reset_terminal=False)
        lv_env = self._env(config)['LV']
        self.assertEqual('-c', lv_env)

    def test_lv_env_nocolor(self) -> None:
        config = command.PagerConfig(color=False,
                                     line_buffering_requested=False,
                                     reset_terminal=False)
        self.assertNotIn('LV', self._env(config))

    def test_lv_env_reset(self) -> None:
        config = command.PagerConfig(color=True,
                                     line_buffering_requested=False,
                                     reset_terminal=True)
        lv_env = self._env(config)['LV']
        self.assertEqual('-c', lv_env)

    def test_lv_env_nocolor_reset(self) -> None:
        config = command.PagerConfig(color=False,
                                     line_buffering_requested=False,
                                     reset_terminal=True)
        self.assertNotIn('LV', self._env(config))

    def test_lv_env_linebuffered(self) -> None:
        config = command.PagerConfig(color=True,
                                     line_buffering_requested=True,
                                     reset_terminal=False)
        lv_env = self._env(config)['LV']
        self.assertEqual('-c', lv_env)

    def test_lv_env_linebuffered_reset(self) -> None:
        config = command.PagerConfig(color=True,
                                     line_buffering_requested=True,
                                     reset_terminal=True)
        lv_env = self._env(config)['LV']
        self.assertEqual('-c', lv_env)

    def test_lv_env_linebuffered_nocolor(self) -> None:
        config = command.PagerConfig(color=False,
                                     line_buffering_requested=True,
                                     reset_terminal=False)
        self.assertNotIn('LV', self._env(config))

    def test_lv_env_linebuffered_nocolor_reset(self) -> None:
        config = command.PagerConfig(color=False,
                                     line_buffering_requested=True,
                                     reset_terminal=True)
        self.assertNotIn('LV', self._env(config))

    def test_lv_env_override(self) -> None:
        config = command.PagerConfig(color=True,
                                     line_buffering_requested=False,
                                     reset_terminal=False)
        with fixtures.EnvironmentVariable('LV', 'abc'):
            env = self._env(config)
        self.assertNotIn('LV', env)


class DefaultTest(LessTest, LVTest):
    def setUp(self) -> None:
        with fixtures.EnvironmentVariable('PAGER', 'less "-r" +F'):
            self.cmd = command.DefaultPager()

    def test_cmd(self) -> None:
        self.assertEqual(['less', '-r', '+F'], self.cmd.command())

    def test_default_cmd(self) -> None:
        with fixtures.EnvironmentVariable('PAGER'):
            cmd = command.DefaultPager()
        self.assertEqual(command.PlatformPager().command(),
                         cmd.command())


class UserSpecifiedTest(DefaultTest):
    def setUp(self) -> None:
        with fixtures.EnvironmentVariable('FOO_PAGER', 'less "-r" +F'):
            self.cmd = command.UserSpecifiedPager('FOO_PAGER')

    def test_env_var_priority_cmd(self) -> None:
        with fixtures.EnvironmentVariable('FOO', 'foo'):
            cmd = command.UserSpecifiedPager('FOO', 'BAR')
        self.assertEqual(['foo'], cmd.command())

    def test_env_var_fallthrough_cmd(self) -> None:
        with fixtures.EnvironmentVariable('BAR', 'bar'):
            cmd = command.UserSpecifiedPager('FOO', 'BAR')
        self.assertEqual(['bar'], cmd.command())

    def test_default_cmd(self) -> None:
        with fixtures.EnvironmentVariable('FOO'):
            with fixtures.EnvironmentVariable('BAR'):
                cmd = command.UserSpecifiedPager('FOO', 'BAR')
        self.assertEqual(command.PlatformPager().command(),
                         cmd.command())


class PlatformFixture(fixtures.Fixture):
    def __init__(self, platform: str):
        self.platform = platform

    def _setUp(self) -> None:
        self.addCleanup(setattr, sys, 'platform', sys.platform)
        sys.platform = self.platform


class PlatformTest(unittest.TestCase):
    def test_aix_cmd(self) -> None:
        with PlatformFixture('aix'):
            cmd = command.PlatformPager()
            self.assertEqual(['more'], cmd.command())

        # Prior to Python 3.8, the version number was included
        with PlatformFixture('aix7'):
            cmd = command.PlatformPager()
            self.assertEqual(['more'], cmd.command())

    def test_linux_cmd(self) -> None:
        with PlatformFixture('linux'):
            cmd = command.PlatformPager()
            self.assertEqual(['less'], cmd.command())

    def test_win32_cmd(self) -> None:
        with PlatformFixture('win32'):
            cmd = command.PlatformPager()
            self.assertEqual(['more.com'], cmd.command())

    def test_cygwin_cmd(self) -> None:
        with PlatformFixture('cygwin'):
            cmd = command.PlatformPager()
            self.assertEqual(['less'], cmd.command())

    def test_macos_cmd(self) -> None:
        with PlatformFixture('darwin'):
            cmd = command.PlatformPager()
            self.assertEqual(['less'], cmd.command())

    def test_sunos_cmd(self) -> None:
        with PlatformFixture('sunos5'):
            cmd = command.PlatformPager()
            self.assertEqual(['less'], cmd.command())

    def test_freebsd_cmd(self) -> None:
        with PlatformFixture('freebsd8'):
            cmd = command.PlatformPager()
            self.assertEqual(['less'], cmd.command())


class GetPagerCommandTest(unittest.TestCase):
    def test_instance(self) -> None:
        cmd = command.PlatformPager()
        self.assertIs(cmd, command.get_pager_command(cmd))

    def test_subclass(self) -> None:
        cls = command.Less
        self.assertIsInstance(command.get_pager_command(cls), cls)

    def test_func(self) -> None:
        func = command.PlatformPager
        self.assertIsInstance(command.get_pager_command(func), type(func()))

    def test_string(self) -> None:
        cmd = command.get_pager_command('foo bar')
        self.assertIsInstance(cmd, command.CustomPager)
        self.assertEqual(['foo', 'bar'], cmd.command())

    def test_list(self) -> None:
        with fixtures.EnvironmentVariable('FOO', 'foo'):
            cmd = command.get_pager_command(['FOO', 'BAR'])
        self.assertIsInstance(cmd, command.CustomPager)
        self.assertEqual(['foo'], cmd.command())

    def test_int(self) -> None:
        self.assertRaises(TypeError, command.get_pager_command, 42)

    def test_list_int(self) -> None:
        self.assertRaises(TypeError, command.get_pager_command, ['FOO', 42])
