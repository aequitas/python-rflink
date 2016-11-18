"""Manager for Rflink gateway/devices."""

import asyncio
from functools import partial

from serial_asyncio import create_serial_connection

from .protocol import RflinkProtocol


class Rflink:
    """Managed communication with Rflink gateway, track device status."""

    def __init__(self, *args, **kwargs):
        """Setup the manager."""
        loop = kwargs.pop('loop', None)

        # use default protocol in not specified
        rflink_protocol = partial(RflinkProtocol, loop, self.handle_packet)
        protocol = kwargs.pop('protocol', rflink_protocol)

        # setup serial connection if no transport specified
        self.transport = kwargs.pop('transport', create_serial_connection(
            loop, protocol, *args, **kwargs
        ))

    @asyncio.coroutine
    def run(self):
        """Initialize asyncio serial transport."""
        self.writer, _ = yield from self.transport

    def send_command(self, protocol, address, switch, action):
        """Send device command to rflink gateway."""
        self.send_packet([
            protocol,
            address,
            switch,
            action,
        ])

    def send_packet(self, fields):
        """Concat fields and send packet to gateway."""
        fields = ['10'] + fields + ['\r\n']
        data = ';'.join(fields).encode()
        self.writer.write(data)

    def handle_packet(self, packet):
        """Handle incoming packet from rflink gateway."""
        if packet.get('id'):
            if len(packet['id']) != 6:
                packet['id'] = '0000' + packet['id']
            self.send_command(packet['protocol'], packet['id'], packet['switch'], 'OFF')
