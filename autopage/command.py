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

import abc
import collections
import collections.abc
import os
import sys

import typing
from typing import Optional, Dict, List


__all__ = ['DefaultPager', 'UserSpecifiedPager', 'PlatformPager',
           'CustomPager',
           'More', 'Less', 'LV']


PagerConfig = collections.namedtuple('PagerConfig', [
        'color',
        'line_buffering_requested',
        'reset_terminal',
    ])


class PagerCommand(metaclass=abc.ABCMeta):
    """
    Abstract base class for pager commands.

    A subclass implementing this interface can be used to specify a particular
    pager command to run and its environment.
    """

    @abc.abstractmethod
    def command(self) -> List[str]:
        """Return the list of command arguments."""
        return ['more']

    @abc.abstractmethod
    def environment_variables(self,
                              config: PagerConfig) -> Optional[Dict[str, str]]:
        """Return the dict of any environment variables to set."""
        return None


class More(PagerCommand):
    """The pager command ``more``."""

    def command(self) -> List[str]:
        if sys.platform.startswith('win32'):
            return ['more.com']
        return ['more']

    def environment_variables(self,
                              config: PagerConfig) -> Optional[Dict[str, str]]:
        return None


class Less(PagerCommand):
    """The pager command ``less``."""

    def command(self) -> List[str]:
        return ['less']

    def environment_variables(self,
                              config: PagerConfig) -> Optional[Dict[str, str]]:
        flags = []
        if config.color:
            # This option will cause less to output ANSI color escape sequences
            # in raw form.
            # Equivalent to the --RAW-CONTROL-CHARS argument
            flags.append('R')
        if not config.line_buffering_requested and not config.reset_terminal:
            # This option will cause less to buffer until an entire screen's
            # worth of data is available (or the EOF is reached), so don't
            # enable it when line buffering is explicitly requested. It also
            # does not reset the terminal after exiting, so don't enable it
            # when resetting the terminal is requested.
            # Equivalent to the --quit-if-one-screen argument
            flags.append('F')
        if not config.reset_terminal:
            # This option will cause less to not reset the terminal after
            # exiting.
            # Equivalent to the --no-init argument
            flags.append('X')

        if flags and (os.getenv('LESS') is None):
            return {
                'LESS': ''.join(flags)
            }
        return None


class LV(PagerCommand):
    """The pager command ``lv``."""

    def command(self) -> List[str]:
        return ['lv']

    def environment_variables(self,
                              config: PagerConfig) -> Optional[Dict[str, str]]:
        if config.color and (os.getenv('LV') is None):
            return {
                # This option allows ANSI color escape sequences in lv
                'LV': '-c',
            }
        return None


class CustomPager(PagerCommand):
    """A pager command parsed from a user-specified string."""
    def __init__(self, pager_cmdline: str):
        import shlex
        self._cmd = shlex.split(pager_cmdline)

    def command(self) -> List[str]:
        return self._cmd

    def environment_variables(self,
                              config: PagerConfig) -> Optional[Dict[str, str]]:
        env = {}
        for cmd_provider in (Less, LV):
            cmd_env = cmd_provider().environment_variables(config)
            if cmd_env:
                env.update(cmd_env)
        return env or None


def PlatformPager() -> PagerCommand:
    """
    Return the default pager command for the current platform.
    """
    if sys.platform.startswith('aix'):
        return More()
    if sys.platform.startswith('win32'):
        return More()
    return Less()


def UserSpecifiedPager(*env_vars: str) -> PagerCommand:
    """
    Return the pager command for the current environment.

    Each of the specified environment variables is searched in order; the first
    one that is set will be used as the pager command. If none of the
    environment variables is set, the default pager for the platform will be
    used.
    """
    for env_var in env_vars:
        env_pager = os.getenv(env_var)
        if env_pager:
            return CustomPager(env_pager)
    return PlatformPager()


def DefaultPager() -> PagerCommand:
    """
    Return the default pager command for the current environment.

    If there is a $PAGER environment variable configured, this command will be
    used. Otherwise, the default pager for the platform will be used.
    """

    if os.name == 'posix':
        # Check that we are not running with elevated privileges
        if os.getuid() not in {0, os.geteuid()}:
            return PlatformPager()
    return UserSpecifiedPager('PAGER')


CommandType = typing.Union[PagerCommand,
                           typing.Callable[[], PagerCommand],
                           str,
                           typing.Sequence[str]]


def get_pager_command(pager_command: CommandType) -> PagerCommand:
    if isinstance(pager_command, PagerCommand):
        return pager_command

    if isinstance(pager_command, str):
        return CustomPager(pager_command)

    if isinstance(pager_command, collections.abc.Sequence):
        return UserSpecifiedPager(*pager_command)

    if callable(pager_command):
        cmd = pager_command()
        if isinstance(cmd, PagerCommand):
            return cmd

    raise TypeError('Invalid type for ``pager_command``')
