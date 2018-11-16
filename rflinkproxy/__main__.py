"""Command line interface for rflink proxy.

Usage:
  rflinkproxy [-v | -vv] [options]
  rflinkproxy (-h | --help)
  rflinkproxy --version

Options:
  --listenport=<port>  Port to listen on
  --port=<port>        Serial port to connect to [default: /dev/ttyACM0],
                         or TCP port in TCP mode.
  --baud=<baud>        Serial baud rate [default: 57600].
  --host=<host>        TCP mode, connect to host instead of serial port.
  --repeat=<repeat>    How often to repeat a command [default: 1].
  -h --help            Show this screen.
  -v                   Increase verbosity
  --version            Show version.
"""

import asyncio
import logging
import sys
from functools import partial
from typing import Any, Callable, Dict, cast

import async_timeout
import pkg_resources
from docopt import docopt
from serial_asyncio import create_serial_connection

from rflink.parser import (
    DELIM,
    PacketHeader,
    decode_packet,
    serialize_packet_id,
    valid_packet
)
from rflink.protocol import RflinkProtocol

log = logging.getLogger(__name__)

CRLF = b'\r\n'
DEFAULT_RECONNECT_INTERVAL = 10
DEFAULT_SIGNAL_REPETITIONS = 1
CONNECTION_TIMEOUT = 10

clients = []


class ProxyProtocol(RflinkProtocol):
    """Proxy commands received to multiple clients."""

    def __init__(self, *args, raw_callback: Callable = None,
                 **kwargs) -> None:
        """Add proxy specific initialization."""
        super().__init__(*args, **kwargs)
        self.raw_callback = raw_callback

    def handle_raw_packet(self, raw_packet):
        """Parse raw packet string into packet dict."""
        log.debug('got packet: %s', raw_packet)
        packet = None
        try:
            packet = decode_packet(raw_packet)
        except:
            log.exception('failed to parse packet: %s', packet)

        log.debug('decoded packet: %s', packet)

        if packet:
            if 'ok' in packet:
                # handle response packets internally
                log.debug('command response: %s', packet)
                self._last_ack = packet
                self._command_ack.set()
            elif self.raw_callback:
                self.raw_callback(raw_packet)
        else:
            log.warning('no valid packet')


def decode_tx_packet(packet: str) -> dict:
    """Break packet down into primitives, and do basic interpretation.

    >>> decode_packet('10;Kaku;ID=41;SWITCH=1;CMD=ON;') == {
    ...     'node': 'gateway',
    ...     'protocol': 'kaku',
    ...     'id': '000041',
    ...     'switch': '1',
    ...     'command': 'on',
    ... }
    True
    """
    node_id, protocol, attrs = packet.split(DELIM, 2)

    data = cast(Dict[str, Any], {
        'node': PacketHeader(node_id).name,
    })

    data['protocol'] = protocol.lower()

    for i, attr in enumerate(filter(None, attrs.strip(DELIM).split(DELIM))):
        if i == 0:
            data['id'] = attr
        if i == 1:
            data['switch'] = attr
        if i == 2:
            data['command'] = attr

    # correct KaKu device address
    if data.get('protocol', '') == 'kaku' and len(data['id']) != 6:
        data['id'] = '0000' + data['id']

    return data


class RFLinkProxy:
    """Proxy commands received to multiple clients."""

    def __init__(self, port=None, host=None, baud=57600, loop=None):
        """Initialize class."""
        self.port = port
        self.host = host
        self.baud = baud
        self.loop = loop
        self.protocol = None
        self.transport = None
        self.closing = False

    @asyncio.coroutine
    def handle_raw_tx_packet(self, writer, raw_packet):
        """Parse raw packet string into packet dict."""
        peer = writer.get_extra_info('peername')
        log.debug(' %s:%s: processing data: %s', peer[0], peer[1], raw_packet)
        packet = None
        try:
            packet = decode_tx_packet(raw_packet)
        except:
            log.exception(' %s:%s: failed to parse packet: %s',
                          peer[0], peer[1], packet)

        log.debug(' %s:%s: decoded packet: %s', peer[0], peer[1], packet)
        if self.protocol and packet:
            if not ';PING;' in raw_packet:
                log.info(' %s:%s: forwarding packet %s to RFLink', peer[0], peer[1], raw_packet)
            else:
                log.debug(' %s:%s: forwarding packet %s to RFLink', peer[0], peer[1], raw_packet)
            yield from self.forward_packet(writer, packet, raw_packet)
        else:
            log.warning(' %s:%s: no valid packet %s', peer[0], peer[1], packet)

    @asyncio.coroutine
    def forward_packet(self, writer, packet, raw_packet):
        """Forward packet from client to RFLink."""
        peer = writer.get_extra_info('peername')
        log.debug(' %s:%s: forwarding data: %s', peer[0], peer[1], packet)
        if 'command' in packet:
            packet_id = serialize_packet_id(packet)
            command = packet['command']
            ack = yield from self.protocol.send_command_ack(
                packet_id, command)
            if ack:
                writer.write("20;00;OK;".encode() + CRLF)
            for _ in range(DEFAULT_SIGNAL_REPETITIONS-1):
                yield from self.protocol.send_command_ack(
                    packet_id, command)
        else:
            self.protocol.send_raw_packet(raw_packet)

    @asyncio.coroutine
    def client_connected_callback(self, reader, writer):
        """Handle connected client."""
        peer = writer.get_extra_info('peername')
        clients.append((reader, writer, peer))
        log.info("Incoming connection from: %s:%s", peer[0], peer[1])
        try:
            while True:
                data = yield from reader.readline()
                if not data:
                    break
                try:
                    line = data.decode().strip()
                except UnicodeDecodeError:
                    line = '\x00'

                # Workaround for domoticz issue #2816
                if line[-1] != DELIM:
                    line = line + DELIM

                if valid_packet(line):
                    yield from self.handle_raw_tx_packet(writer, line)
                else:
                    log.warning(" %s:%s: dropping invalid data: '%s'", peer[0], peer[1], line)
                    pass
        except ConnectionResetError:
            pass
        except Exception as e:
            log.exception(e)

        log.info("Disconnected from: %s:%s", peer[0], peer[1])
        writer.close()
        clients.remove((reader, writer, peer))

    def raw_callback(self, raw_packet):
        """Send data to all connected clients."""
        if not ';PONG;' in raw_packet:
            log.info('forwarding packet %s to clients', raw_packet)
        else:
            log.debug('forwarding packet %s to clients', raw_packet)
        writers = [i[1] for i in list(clients)]
        for writer in writers:
            writer.write(str(raw_packet).encode() + CRLF)

    def reconnect(self, exc=None):
        """Schedule reconnect after connection has been unexpectedly lost."""
        # Reset protocol binding before starting reconnect
        self.protocol = None

        if not self.closing:
            log.warning('disconnected from Rflink, reconnecting')
            self.loop.create_task(self.connect())

    async def connect(self):
        """Set up connection and hook it into HA for reconnect/shutdown."""
        import serial

        log.info('Initiating Rflink connection')

        # Rflink create_rflink_connection decides based on the value of host
        # (string or None) if serial or tcp mode should be used

        # Setup protocol
        protocol = partial(
            ProxyProtocol,
            disconnect_callback=self.reconnect,
            raw_callback=self.raw_callback,
            loop=self.loop,
        )

        # Initiate serial/tcp connection to Rflink gateway
        if self.host:
            connection = self.loop.create_connection(protocol, self.host, self.port)
        else:
            connection = create_serial_connection(self.loop, protocol, self.port, self.baud)

        try:
            with async_timeout.timeout(CONNECTION_TIMEOUT,
                                       loop=self.loop):
                self.transport, self.protocol = await connection

        except (serial.serialutil.SerialException, ConnectionRefusedError,
                TimeoutError, OSError, asyncio.TimeoutError) as exc:
            reconnect_interval = DEFAULT_RECONNECT_INTERVAL
            log.error(
                "Error connecting to Rflink, reconnecting in %s",
                reconnect_interval)

            self.loop.call_later(reconnect_interval, self.reconnect, exc)
            return

        log.info('Connected to Rflink')


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

    host = args['--host']
    port = args['--port']
    baud = args['--baud']
    listenport = args['--listenport']

    proxy = RFLinkProxy(port=port, host=host, baud=baud, loop=loop)

    server_coro = asyncio.start_server(
        proxy.client_connected_callback,
        host="",
        port=listenport,
        loop=loop,
    )

    server = loop.run_until_complete(server_coro)
    addr = server.sockets[0].getsockname()
    log.info('Serving on %s', addr)

    conn_coro = proxy.connect()
    loop.run_until_complete(conn_coro)

    proxy.closing = False
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        proxy.closing = True

        # cleanup server
        server.close()
        loop.run_until_complete(server.wait_closed())

        # cleanup server connections
        writers = [i[1] for i in list(clients)]
        for writer in writers:
            writer.close()
            if sys.version_info >= (3, 7):
                loop.run_until_complete(writer.wait_closed())

        # cleanup RFLink connection
        proxy.transport.close()

    finally:
        loop.close()
