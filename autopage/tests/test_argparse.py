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

import argparse

import fixtures

import autopage
import autopage.argparse


class ArgumentParseTest(fixtures.TestWithFixtures):
    def setUp(self):
        patch_ap = self.useFixture(fixtures.MockPatch('autopage.AutoPager'))
        self.pager = patch_ap.mock

    def test_argparse(self, module=autopage.argparse):
        parser = module.ArgumentParser()
        try:
            parser.parse_args(['foo', '--help'])
        except SystemExit as exit:
            self.assertIs(self.pager.return_value.exit_code.return_value,
                          exit.code)
        self.pager.assert_called_once_with(reset_on_exit=False)
        self.pager.return_value.__enter__.assert_called_once()

    def test_monkey_patch(self):
        patch = self.useFixture(fixtures.MockPatch('argparse._HelpAction'))
        autopage.argparse.monkey_patch()
        self.assertIsNot(patch.mock, argparse._HelpAction)
        self.test_argparse(argparse)

    def test_monkey_patch_context(self):
        patch = self.useFixture(fixtures.MockPatch('argparse._HelpAction'))
        with autopage.argparse.monkey_patch():
            self.assertIsNot(patch.mock, argparse._HelpAction)
            self.test_argparse(argparse)
        self.assertIs(patch.mock, argparse._HelpAction)
