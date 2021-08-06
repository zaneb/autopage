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

import fixtures

from autopage import command


class MoreTest(unittest.TestCase):
    def setUp(self):
        self.cmd = command.More()

    def test_cmd(self):
        self.assertEqual(['more'], self.cmd.command())

    def test_less_env_defaults(self):
        config = command.PagerConfig(color=True,
                                     line_buffering_requested=False,
                                     reset_terminal=False)
        self.assertIsNone(self.cmd.environment_variables(config))


class LessTest(unittest.TestCase):
    def setUp(self):
        self.cmd = command.Less()

    def test_cmd(self):
        self.assertEqual(['less'], self.cmd.command())

    def test_less_env_defaults(self):
        config = command.PagerConfig(color=True,
                                     line_buffering_requested=False,
                                     reset_terminal=False)
        less_env = self.cmd.environment_variables(config)['LESS']
        self.assertEqual('RFX', less_env)

    def test_less_env_nocolor(self):
        config = command.PagerConfig(color=False,
                                     line_buffering_requested=False,
                                     reset_terminal=False)
        less_env = self.cmd.environment_variables(config)['LESS']
        self.assertEqual('FX', less_env)

    def test_less_env_reset(self):
        config = command.PagerConfig(color=True,
                                     line_buffering_requested=False,
                                     reset_terminal=True)
        less_env = self.cmd.environment_variables(config)['LESS']
        self.assertEqual('R', less_env)

    def test_less_env_nocolor_reset(self):
        config = command.PagerConfig(color=False,
                                     line_buffering_requested=False,
                                     reset_terminal=True)
        self.assertNotIn('LESS', self.cmd.environment_variables(config) or {})

    def test_less_env_linebuffered(self):
        config = command.PagerConfig(color=True,
                                     line_buffering_requested=True,
                                     reset_terminal=False)
        less_env = self.cmd.environment_variables(config)['LESS']
        self.assertEqual('RX', less_env)

    def test_less_env_linebuffered_reset(self):
        config = command.PagerConfig(color=True,
                                     line_buffering_requested=True,
                                     reset_terminal=True)
        less_env = self.cmd.environment_variables(config)['LESS']
        self.assertEqual('R', less_env)

    def test_less_env_linebuffered_nocolor(self):
        config = command.PagerConfig(color=False,
                                     line_buffering_requested=True,
                                     reset_terminal=False)
        less_env = self.cmd.environment_variables(config)['LESS']
        self.assertEqual('X', less_env)

    def test_less_env_linebuffered_nocolor_reset(self):
        config = command.PagerConfig(color=False,
                                     line_buffering_requested=True,
                                     reset_terminal=True)
        self.assertNotIn('LESS', self.cmd.environment_variables(config) or {})

    def test_less_env_override(self):
        config = command.PagerConfig(color=True,
                                     line_buffering_requested=False,
                                     reset_terminal=False)
        with fixtures.EnvironmentVariable('LESS', 'abc'):
            env = self.cmd.environment_variables(config) or {}
        self.assertNotIn('LESS', env)


class LVTest(unittest.TestCase):
    def setUp(self):
        self.cmd = command.LV()

    def test_cmd(self):
        self.assertEqual(['lv'], self.cmd.command())

    def test_lv_env_defaults(self):
        config = command.PagerConfig(color=True,
                                     line_buffering_requested=False,
                                     reset_terminal=False)
        lv_env = self.cmd.environment_variables(config)['LV']
        self.assertEqual('-c', lv_env)

    def test_lv_env_nocolor(self):
        config = command.PagerConfig(color=False,
                                     line_buffering_requested=False,
                                     reset_terminal=False)
        self.assertNotIn('LV', self.cmd.environment_variables(config) or {})

    def test_lv_env_reset(self):
        config = command.PagerConfig(color=True,
                                     line_buffering_requested=False,
                                     reset_terminal=True)
        lv_env = self.cmd.environment_variables(config)['LV']
        self.assertEqual('-c', lv_env)

    def test_lv_env_nocolor_reset(self):
        config = command.PagerConfig(color=False,
                                     line_buffering_requested=False,
                                     reset_terminal=True)
        self.assertNotIn('LV', self.cmd.environment_variables(config) or {})

    def test_lv_env_linebuffered(self):
        config = command.PagerConfig(color=True,
                                     line_buffering_requested=True,
                                     reset_terminal=False)
        lv_env = self.cmd.environment_variables(config)['LV']
        self.assertEqual('-c', lv_env)

    def test_lv_env_linebuffered_reset(self):
        config = command.PagerConfig(color=True,
                                     line_buffering_requested=True,
                                     reset_terminal=True)
        lv_env = self.cmd.environment_variables(config)['LV']
        self.assertEqual('-c', lv_env)

    def test_lv_env_linebuffered_nocolor(self):
        config = command.PagerConfig(color=False,
                                     line_buffering_requested=True,
                                     reset_terminal=False)
        self.assertNotIn('LV', self.cmd.environment_variables(config) or {})

    def test_lv_env_linebuffered_nocolor_reset(self):
        config = command.PagerConfig(color=False,
                                     line_buffering_requested=True,
                                     reset_terminal=True)
        self.assertNotIn('LV', self.cmd.environment_variables(config) or {})

    def test_lv_env_override(self):
        config = command.PagerConfig(color=True,
                                     line_buffering_requested=False,
                                     reset_terminal=False)
        with fixtures.EnvironmentVariable('LV', 'abc'):
            env = self.cmd.environment_variables(config) or {}
        self.assertNotIn('LV', env)


class DefaultTest(LessTest, LVTest):
    def setUp(self):
        with fixtures.EnvironmentVariable('PAGER', 'less "-r" +F'):
            self.cmd = command.DefaultPager()

    def test_cmd(self):
        self.assertEqual(['less', '-r', '+F'], self.cmd.command())

    def test_default_cmd(self):
        with fixtures.EnvironmentVariable('PAGER'):
            cmd = command.DefaultPager()
        self.assertEqual(command.PlatformPager().command(),
                         cmd.command())


class PlatformFixture(fixtures.Fixture):
    def __init__(self, platform):
        self.platform = platform

    def _setUp(self):
        self.addCleanup(setattr, sys, 'platform', sys.platform)
        sys.platform = self.platform


class PlatformTest(unittest.TestCase):
    def test_aix_cmd(self):
        with PlatformFixture('aix'):
            cmd = command.PlatformPager()
            self.assertEqual(['more'], cmd.command())

        # Prior to Python 3.8, the version number was included
        with PlatformFixture('aix7'):
            cmd = command.PlatformPager()
            self.assertEqual(['more'], cmd.command())

    def test_linux_cmd(self):
        with PlatformFixture('linux'):
            cmd = command.PlatformPager()
            self.assertEqual(['less'], cmd.command())

    def test_win32_cmd(self):
        with PlatformFixture('win32'):
            cmd = command.PlatformPager()
            self.assertEqual(['more.com'], cmd.command())

    def test_cygwin_cmd(self):
        with PlatformFixture('cygwin'):
            cmd = command.PlatformPager()
            self.assertEqual(['less'], cmd.command())

    def test_macos_cmd(self):
        with PlatformFixture('darwin'):
            cmd = command.PlatformPager()
            self.assertEqual(['less'], cmd.command())

    def test_sunos_cmd(self):
        with PlatformFixture('sunos5'):
            cmd = command.PlatformPager()
            self.assertEqual(['less'], cmd.command())

    def test_freebsd_cmd(self):
        with PlatformFixture('freebsd8'):
            cmd = command.PlatformPager()
            self.assertEqual(['less'], cmd.command())
