"""Asyncio protocol implementation of RFlink."""

import asyncio
import logging

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

    def connection_made(self, transport):
        """Just logging for now."""
        self.transport = transport
        self.log.debug('connected')

    def data_received(self, data):
        """Assemble incoming data into per line packets."""
        data = data.decode()
        self.log.debug('received data: %s', data.strip())

        if '\n' in data:
            end_old, * begin_new = data.splitlines()
            asyncio.ensure_future(self.handle_packet(self.packet + end_old))
            if begin_new:
                self.packet = begin_new[0]
            else:
                self.packet = ''
        else:
            self.packet += data

    def connection_lost(self, exc):
        """Stop when connection is lost."""
        self.log.error('disconnected')
        self.loop.stop()

    @asyncio.coroutine
    def handle_packet(self, packet):
        """Fire packet callback."""
        self.log.debug('got packet: %s', packet)
        self.log.info(parse_packet(packet))
