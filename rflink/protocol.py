"""Asyncio protocol implementation of RFlink."""
import asyncio
import logging
import re
from functools import partial

from serial_asyncio import create_serial_connection

from .parser import parse_packet

log = logging.getLogger(__name__)


class ProtocolBase(asyncio.Protocol):
    """Manage low level rflink protocol."""

    transport = None

    def __init__(self, loop, packet_callback=None):
        """Initialize class."""
        self.loop = loop
        self.packet_callback = packet_callback
        self.packet = ''
        self.start_packet = re.compile('^(10|11|20);').match
        self.buffer = ''

    def connection_made(self, transport):
        """Just logging for now."""
        self.transport = transport
        log.debug('connected')

    def data_received(self, data):
        """Add incoming data to buffer."""
        data = data.decode()
        log.debug('received data: %s', data.strip())
        self.buffer += data
        self.handle_lines()

    def handle_lines(self):
        """Assemble incoming data into per-line packets."""
        while "\r\n" in self.buffer:
            line, self.buffer = self.buffer.split("\r\n", 1)
            if self.start_packet(line):
                self.handle_raw_packet(line)

    def connection_lost(self, exc):
        """Stop when connection is lost."""
        log.error('disconnected')
        self.loop.stop()


class PacketHandling:
    """Handle translating rflink packets."""

    def handle_raw_packet(self, raw_packet):
        """Callback for handling incoming raw packets."""
        log.debug('got packet: %s', raw_packet)
        packet = None
        try:
            packet = parse_packet(raw_packet)
        except:
            log.exception('failed to parse packet: %s', packet)

        if packet:
            self.handle_packet(packet)

    def handle_packet(self, packet):
        """Callback for handling incoming parsed packets."""
        log.debug('parsed packet: %s', packet)
        if self.packet_callback:
            self.packet_callback(packet)
        else:
            print(packet)

    def send_command(self, protocol, address, switch, action):
        """Send device command to rflink gateway."""
        command = [protocol, address, switch, action]
        log.debug('sending command: %s', command)
        self.send_packet(command)

    def send_packet(self, fields):
        """Concat fields and send packet to gateway."""
        fields = ['10'] + fields
        data = ';'.join(fields + ['\r\n']).encode()
        self.transport.write(data)


class RflinkProtocol(PacketHandling, ProtocolBase):
    """Combine low and high level protocol handling."""


class InverterProtocol(RflinkProtocol):
    """Invert switch commands received and send them out."""

    def handle_packet(self, packet):
        """Handle incoming packet from rflink gateway."""
        if packet.get('switch'):
            if packet['command'] == 'on':
                cmd = 'off'
            else:
                cmd = 'on'
            self.send_command(packet['protocol'], packet['id'],
                              packet['switch'], cmd)


class RepeaterProtocol(RflinkProtocol):
    """Repeat switch commands received."""

    def handle_packet(self, packet):
        """Handle incoming packet from rflink gateway."""
        if packet.get('switch'):
            self.send_command(packet['protocol'], packet['id'],
                              packet['switch'], packet['command'])


def create_rflink_connection(*args, **kwargs):
    """Create Rflink manager class, returns transport coroutine."""
    loop = kwargs.pop('loop', asyncio.get_event_loop())

    # use default protocol if not specified
    rflink_protocol = kwargs.pop('protocol', RflinkProtocol)
    packet_callback = kwargs.pop('packet_callback', None)
    protocol = partial(rflink_protocol, loop, packet_callback=packet_callback)

    # setup serial connection if no transport specified
    host = kwargs.pop('host', None)
    port = kwargs.pop('port')
    if host:
        conn = loop.create_connection(protocol, host, port)
    else:
        baud = kwargs.get('baud', 57600)
        conn = create_serial_connection(loop, protocol, port, baud)

    return conn
