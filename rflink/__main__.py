"""Command line interface for rflink library.

Usage:
  rflink [-v] [--port=<port> [--baud=<baud>] | --host=<host> --port=<port>]
  rflink (-h | --help)
  rflink --version

Options:
  -p --port=<port>  Serial port to connect to [default: /dev/ttyACM0],
                        or TCP port in TCP mode.
  --baud=<baud>     Serial baud rate [default: 57600].
  --host=<host>     TCP mode, connect to host instead of serial port.
  -h --help         Show this screen.
  -v --verbose      Increase verbosity
  --version         Show version.

"""

import asyncio
import logging
from functools import partial

import pkg_resources
from docopt import docopt

from serial_asyncio import create_serial_connection

from .protocol import RflinkProtocol


def main():
    """Parse argument and setup main program loop."""
    args = docopt(__doc__, version=pkg_resources.require('rflink')[0].version)

    if args['--verbose']:
        level = logging.DEBUG
    else:
        level = logging.INFO
    logging.basicConfig(level=level)

    loop = asyncio.get_event_loop()

    protocol = partial(RflinkProtocol, loop)
    if args.get('--host'):
        conn = loop.create_connection(loop, protocol,
            args['--host'], args['--port'])
    else:
        conn = create_serial_connection(loop, protocol,
            args['--port'], args['--baud'])

    try:
        loop.run_until_complete(conn)
        loop.run_forever()
    finally:
        loop.close()
