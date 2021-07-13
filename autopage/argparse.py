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
import functools
import types
from typing import Any, Sequence, Text, TextIO, Tuple, Type, Optional, Union
from typing import Callable, ContextManager, Generator

import autopage

from argparse import *  # noqa


_HelpFormatter = argparse.HelpFormatter

_color_attr = '_autopage_color'


def help_pager(out_stream: Optional[TextIO] = None) -> autopage.AutoPager:
    """Return an AutoPager suitable for help output."""
    return autopage.AutoPager(out_stream,
                              allow_color=True,
                              line_buffering=False,
                              reset_on_exit=False)


def use_color_for_parser(parser: argparse.ArgumentParser,
                         color: bool) -> None:
    """Configure a parser whether to output in color from HelpFormatters."""
    setattr(parser, _color_attr, color)


class ColorHelpFormatter(_HelpFormatter):
    class _Section(_HelpFormatter._Section):  # type: ignore
        @property
        def heading(self) -> Optional[Text]:
            if (not self._heading
                    or self._heading == argparse.SUPPRESS
                    or not getattr(self.formatter, _color_attr, False)):
                return self._heading
            return f'\033[4m{self._heading}\033[0m'

        @heading.setter
        def heading(self, heading: Optional[Text]) -> None:
            self._heading = heading

    def _metavar_formatter(self,
                           action: argparse.Action,
                           default_metavar: Text) -> Callable[[int],
                                                              Tuple[str, ...]]:
        get_metavars = super()._metavar_formatter(action, default_metavar)
        if not getattr(self, _color_attr, False):
            return get_metavars

        def color_metavar(size: int) -> Tuple[str, ...]:
            return tuple(f'\033[3m{mv}\033[0m' for mv in get_metavars(size))
        return color_metavar


class ColorRawDescriptionHelpFormatter(ColorHelpFormatter,
                                       argparse.RawDescriptionHelpFormatter):
    """Help message formatter which retains any formatting in descriptions."""


class ColorRawTextHelpFormatter(ColorHelpFormatter,
                                argparse.RawTextHelpFormatter):
    """Help message formatter which retains formatting of all help text."""


class ColorArgDefaultsHelpFormatter(ColorHelpFormatter,
                                    argparse.ArgumentDefaultsHelpFormatter):
    """Help message formatter which adds default values to argument help."""


class ColorMetavarTypeHelpFormatter(ColorHelpFormatter,
                                    argparse.MetavarTypeHelpFormatter):
    """Help message formatter which uses the argument 'type' as the default
    metavar value (instead of the argument 'dest')"""


class _HelpAction(argparse._HelpAction):
    def __init__(self,
                 option_strings: Sequence[Text],
                 dest: Text = argparse.SUPPRESS,
                 default: Text = argparse.SUPPRESS,
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
        pager = help_pager()
        with pager as out:
            use_color_for_parser(parser, pager.to_terminal())
            parser.print_help(out)
        parser.exit(pager.exit_code())


class _ActionsContainer(argparse._ActionsContainer):
    def __init__(self, *args, **kwargs) -> None:  # type: ignore
        super().__init__(*args, **kwargs)
        self.register('action', 'help', _HelpAction)


def _substitute_formatter(
            get_fmtr: Callable[[Any], _HelpFormatter]
        ) -> Callable[[argparse.ArgumentParser], _HelpFormatter]:
    @functools.wraps(get_fmtr)
    def _get_formatter(parser: argparse.ArgumentParser) -> _HelpFormatter:
        if parser.formatter_class is _HelpFormatter:
            parser.formatter_class = ColorHelpFormatter
        formatter = get_fmtr(parser)
        if isinstance(formatter, ColorHelpFormatter):
            setattr(formatter, _color_attr,
                    getattr(parser, _color_attr, False))
        return formatter
    return _get_formatter


class AutoPageArgumentParser(argparse.ArgumentParser, _ActionsContainer):
    @_substitute_formatter
    def _get_formatter(self) -> _HelpFormatter:
        return super()._get_formatter()


ArgumentParser = AutoPageArgumentParser                         # type: ignore
HelpFormatter = ColorHelpFormatter                              # type: ignore
RawDescriptionHelpFormatter = ColorRawDescriptionHelpFormatter  # type: ignore
RawTextHelpFormatter = ColorRawTextHelpFormatter                # type: ignore
ArgumentDefaultsHelpFormatter = ColorArgDefaultsHelpFormatter   # type: ignore
MetavarTypeHelpFormatter = ColorMetavarTypeHelpFormatter        # type: ignore


def monkey_patch() -> ContextManager:
    """
    Monkey-patch the system argparse module to automatically page help output.

    The result of calling this function can optionally be used as a context
    manager to restore the status quo when it exits.
    """
    import sys

    def get_existing_classes(module: types.ModuleType) -> Tuple[Type, ...]:
        return (
            module._HelpAction,                    # type: ignore
            module.HelpFormatter,                  # type: ignore
            module.RawDescriptionHelpFormatter,    # type: ignore
            module.RawTextHelpFormatter,           # type: ignore
            module.ArgumentDefaultsHelpFormatter,  # type: ignore
            module.MetavarTypeHelpFormatter,       # type: ignore
        )  # type: ignore

    def patch_classes(module: types.ModuleType,
                      impl: Tuple[Type, ...]) -> None:
        (
            module._HelpAction,                    # type: ignore
            module.HelpFormatter,                  # type: ignore
            module.RawDescriptionHelpFormatter,    # type: ignore
            module.RawTextHelpFormatter,           # type: ignore
            module.ArgumentDefaultsHelpFormatter,  # type: ignore
            module.MetavarTypeHelpFormatter,       # type: ignore
        ) = impl

    orig = get_existing_classes(argparse)
    orig_fmtr = argparse.ArgumentParser._get_formatter
    patched = get_existing_classes(sys.modules[__name__])
    patch_classes(argparse, patched)
    new_fmtr = _substitute_formatter(orig_fmtr)
    argparse.ArgumentParser._get_formatter = new_fmtr  # type: ignore

    @contextlib.contextmanager
    def unpatcher() -> Generator:
        try:
            yield
        finally:
            patch_classes(argparse, orig)
            argparse.ArgumentParser._get_formatter = orig_fmtr  # type: ignore

    return unpatcher()


__all__ = argparse.__all__ + [  # type: ignore
        'use_color_for_parser', 'monkey_patch'
    ]
