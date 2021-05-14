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

"""
This module provides a drop-in replacement for the standard library argparse
module, with the output of the 'help' action automatically sent to a pager
when appropriate.

To use, replace the code:

    >>> import argparse

with:

    >>> from autopage import argparse

Or, alternatively, call the ``autopage.argparse.monkey_patch()`` function to
monkey-patch the argparse module. This is useful when you do not control the
code that creates the ArgumentParser. The result of calling this function can
also be used as a context manager to ensure that the original functionality is
restored.
"""

import argparse
import contextlib
from typing import Any, Sequence, Text, Optional, Union
from typing import ContextManager, Generator

import autopage

from argparse import *  # noqa


class _HelpAction(argparse._HelpAction):
    def __init__(self,
                 option_strings: Sequence[Text],
                 dest: Text = argparse.SUPPRESS,
                 default: Any = argparse.SUPPRESS,
                 help: Optional[Text] = None) -> None:
        argparse.Action.__init__(
            self,
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help)

    def __call__(self, parser: argparse.ArgumentParser,
                 namespace: argparse.Namespace,
                 values: Union[Text, Sequence[Any], None],
                 option_string: Optional[Text] = None) -> None:
        pager = autopage.AutoPager(reset_on_exit=False)
        with pager as out:
            parser.print_help(out)
        parser.exit(pager.exit_code())


class _ActionsContainer(argparse._ActionsContainer):
    def __init__(self, *args, **kwargs) -> None:  # type: ignore
        super().__init__(*args, **kwargs)
        self.register('action', 'help', _HelpAction)


class AutoPageArgumentParser(argparse.ArgumentParser, _ActionsContainer):
    pass


ArgumentParser = AutoPageArgumentParser  # type: ignore


def monkey_patch() -> ContextManager:
    """
    Monkey-patch the system argparse module to automatically page help output.

    The result of calling this function can optionally be used as a context
    manager to restore the status quo when it exits.
    """
    orig_HelpAction = argparse._HelpAction
    argparse._HelpAction = _HelpAction  # type: ignore

    @contextlib.contextmanager
    def unpatcher() -> Generator:
        try:
            yield
        finally:
            argparse._HelpAction = orig_HelpAction  # type: ignore

    return unpatcher()


__all__ = argparse.__all__ + ['monkey_patch']  # type: ignore
