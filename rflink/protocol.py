"""Asyncio protocol implementation of RFlink."""

import asyncio
import logging
import re

from .parser import parse_packet


class RflinkProtocol(asyncio.Protocol):
    """Assemble and handle incoming data."""

    transport = None

    def __init__(self, loop, packet_callback=None):
        """Initialize class."""
        self.loop = loop
        self.log = logging.getLogger(__name__)
        self.packet_callback = packet_callback
        self.packet = ''
        self.start_packet = re.compile('^(10|11|20);').match
        self.buffer = ''

    def connection_made(self, transport):
        """Just logging for now."""
        self.transport = transport
        self.log.debug('connected')

    def data_received(self, data):
        """Add incoming data to buffer."""
        data = data.decode()
        self.log.debug('received data: %s', data.strip())
        self.buffer += data
        self.handle_lines()

    def handle_lines(self):
        """Assemble incoming data into per-line packets."""
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            if self.start_packet(line):
                self.handle_raw_packet(line)

    def connection_lost(self, exc):
        """Stop when connection is lost."""
        self.log.error('disconnected')
        self.loop.stop()

    def handle_raw_packet(self, raw_packet):
        """Callback for handling incoming raw packets."""
        self.log.debug('got packet: %s', raw_packet)
        packet = parse_packet(raw_packet)
        self.handle_packet(packet)

    def handle_packet(self, packet):
        """Callback for handling incoming parsed packets."""
        print(packet)
