# autopage

[Autopage](https://github.com/zaneb/autopage) is a Python library to
automatically display terminal output from a program in a pager (like `less`)
whenever you need it, and never when you don't. And it only takes one line of
code.

You know how some CLI programs like `git` (and a handful of others, including
`man` and `systemctl`) automatically pipe their output to `less`? Except not if
there's less than one screen's worth of data. And if you redirect the output to
a file or a pipe, it does the right thing instead. Colours are preserved. Don't
you wish all programs worked like that? Now at least all of your Python
programs can.

## License

© 2020-2021 by Zane Bitter

Open Source licensed under the terms of the Apache Software License, version
2.0.

## Installation

[Autopage is available from PyPI](https://pypi.org/project/autopage/). The
easiest way to install (preferably in a `virtualenv` virtual environment) is
with `pip`:

    $ pip install autopage

### On Fedora and CentOS/RHEL

Copr repositories are available for Fedora and EPEL. The library can be
installed by first enabling the repository:

    # dnf copr enable zaneb/autopage
    # dnf install python3-autopage

### On Ubuntu

A PPA is available for Ubuntu. The library can be installed by first enabling
the PPA:

    # add-apt-repository ppa:zaneb/autopage
    # apt-get update
    # apt-get install python3-autopage

## Basic Use

The `AutoPager` class provides a context manager that furnishes the output
stream to write to. Here is a basic example that reads from stdin and outputs
to a pager connected to stdout:

```python
import sys
import autopage

with autopage.AutoPager() as out:
    for l in sys.stdin:
        out.write(l)
```

If you are explicitly passing a stream to write to (rather than directly
referencing a global variable such as `sys.stdout` then you may be able to add
automatic paging support with only a single line of code.

## Paging help output

If your program uses the `argparse` module from the standard library, you can
ensure that the help output is automatically paged when possible by changing
the import statement to:

```python
from autopage import argparse
```

If you don't control the module that imports `argparse`, you can instead call
`autopage.argparse.monkey_patch()` to patch the module directly. This function
can also be used as a context manager.

## Environment

The end user can override the pager command by setting the `PAGER` environment
variable. The default command is `less`.

The end user can also override the settings for `less` by setting the `LESS`
environment variable. If not specified, the settings are determined by the
`allow_color` and `line_buffering` options. By default ANSI control characters
for setting colours are respected and the pager will not run if there is less
than a full screen of text to display.

## Line buffering

Normally output streams are buffered so that data is written to the output file
only when the buffer becomes full. This is efficient and generally works fine
as long as the data is being produced as fast as it can be consumed. However,
when the data is streaming at a slower rate than it could be displayed (e.g.
log output from something like `tail -f`) this results in a large delay between
data being produced and consumed. If you have ever tried to grep a streaming
log and pipe the output to a pager then you are familiar with how
unsatisfactory this is.

The solution is to flush the output buffer after each line is written, which is
known as [line
buffering](https://www.pixelbeat.org/programming/stdio_buffering/). The
`AutoPager` class supports a `line_buffering` argument to enable or disable
line buffering. The default is to use the line buffering mode already
configured for the output stream (which is usually to disable line buffering).

When reading from an input stream (which may be a file, pipe, or the console)
and optionally processing the data before outputting it again, the convenience
function `line_buffer_from_input()` returns the optimal line buffering setting
for a given input stream (`sys.stdin` by default).

```python
import sys
import autopage

with autopage.AutoPager(line_buffering=line_buffer_from_input()) as out:
    for l in sys.stdin:
        out.write(l)
```

## Terminal reset

By default, when the pager exits it will leave the latest displayed output on
screen in the terminal. This can be changed by passing `True` for the
`reset_on_exit` argument to the `AutoPager` class. If this option is set, the
terminal will be cleared when the pager exits, returning to its position prior
to starting the pager (as is the case by default when running `less` manually
from the command line).

## Exit code

Programs may wish to return a different exit code if they are interrupted by
the user (either with Ctrl-C or by closing the pager) than if they ran to
completion. The exceptions generated when the pager is closed prematurely are
suppressed, so the `AutoPager` class offers the `exit_code()` method to provide
a suitable exit code for the program. This also takes into account other
exceptions that bubble up through the context manager.

## Complete Example

```python
import sys
import autopage

def process(input_stream, output_stream):
    pager = autopage.AutoPager(
        output_stream,
        line_buffering=autopage.line_buffered_input(input_stream),
        allow_color=True,
        reset_on_exit=True,
        errors=autopage.ErrorStrategy.REPLACE,
    )

    try:
        with pager as out:
            for l in input_stream:
                out.write(l)
    except Exception as exc:
        sys.stderr.write(f'{str(exc)}\n')
    except KeyboardInterrupt:
        pass
    return pager.exit_code()

sys.exit(process(sys.stdin, sys.stdout))
```
