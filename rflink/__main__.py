"""Command line interface for rflink library.

Usage:
  rflink [-v | -vv] [options]
  rflink (-h | --help)
  rflink --version

Options:
  -p --port=<port>   Serial port to connect to [default: /dev/ttyACM0],
                       or TCP port in TCP mode.
  --baud=<baud>      Serial baud rate [default: 57600].
  --host=<host>      TCP mode, connect to host instead of serial port.
  -m=<handling>      How to handle incoming packets [default: event].
  --ignore=<ignore>  List of device ids to ignore, end with * to match wildcard.
  -h --help          Show this screen.
  -v                 Increase verbosity
  --version          Show version.

"""

import asyncio
import logging
import sys

import pkg_resources
from docopt import docopt

from .protocol import (
    EventHandling,
    InverterProtocol,
    PacketHandling,
    RepeaterProtocol,
    create_rflink_connection
)

PROTOCOLS = {
    'event': EventHandling,
    'print': PacketHandling,
    'invert': InverterProtocol,
    'repeat': RepeaterProtocol,
}


def main(argv=sys.argv[1:], loop=None):
    """Parse argument and setup main program loop."""
    args = docopt(__doc__, argv=argv,
                  version=pkg_resources.require('rflink')[0].version)

    level = logging.ERROR
    if args['-v']:
        level = logging.INFO
    if args['-v'] == 2:
        level = logging.DEBUG
    logging.basicConfig(level=level)

    if not loop:
        loop = asyncio.get_event_loop()

    if args['--ignore']:
        ignore = args['--ignore'].split(',')
    else:
        ignore = []

    protocol = PROTOCOLS[args['-m']]
    conn = create_rflink_connection(
        protocol=protocol,
        host=args['--host'],
        port=args['--port'],
        baud=args['--baud'],
        loop=loop,
        ignore=ignore,
    )

    transport, protocol = loop.run_until_complete(conn)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        # cleanup connection
        transport.close()
        loop.run_forever()
    finally:
        loop.close()
