"""Command line interface for rflink library.

Usage:
  rflink [--port=<port>, --baud=<baud>]
  rflink (-h | --help)
  rflink --version

Options:
  -p --port=<port>  Serial port to connect to [default: /dev/ttyACM0].
  --baud=<baud>     Serial baud rate [default: 57600].
  -h --help         Show this screen.
  --version         Show version.

"""

import asyncio

import pkg_resources
from docopt import docopt


@asyncio.coroutine
def output():
    """Provide output to console."""
    import itertools
    counter = itertools.count()
    while True:
        print(next(counter))
        yield from asyncio.sleep(1)


def main():
    """Parse argument and setup main program loop."""
    arguments = docopt(__doc__, version=pkg_resources.require('rflink')[0].version)
    print(arguments)
    loop = asyncio.get_event_loop()
    tasks = asyncio.gather(output())
    try:
        loop.run_until_complete(tasks)
    except KeyboardInterrupt:
        tasks.cancel()
        loop.run_forever()
        tasks.exception()
    finally:
        loop.close()
