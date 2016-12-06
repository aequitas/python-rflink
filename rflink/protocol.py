"""Asyncio protocol implementation of RFlink."""
import asyncio
import concurrent
import logging
from functools import partial

from serial_asyncio import create_serial_connection

from .parser import decode_packet, encode_packet, is_packet_header

log = logging.getLogger(__name__)

TIMEOUT = 5


class ProtocolBase(asyncio.Protocol):
    """Manage low level rflink protocol."""

    transport = None  # type: asyncio.Transport

    def __init__(self, loop, packet_callback=None):
        """Initialize class."""
        self.loop = loop
        self.packet_callback = packet_callback
        self.packet = ''
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
            if is_packet_header(0):
                self.handle_raw_packet(line)

    def send_raw_packet(self, packet: str):
        """Encode and put packet string onto write buffer."""
        data = packet + r'\r\n'
        log.debug('writing data: %s', data)
        self.transport.write(data.encode())

    def connection_lost(self, exc):
        """Stop when connection is lost."""
        log.error('disconnected')
        self.loop.stop()


class PacketHandling:
    """Handle translating rflink packets into python primitives."""

    def __init__(self, *args, **kwargs):
        """Add packethandling specific initialization."""
        super().__init__(*args, **kwargs)
        self._command_ack = asyncio.Event()
        self._ready_to_send = asyncio.Lock()

    def handle_raw_packet(self, raw_packet):
        """Parse raw packet string into packet dict."""
        log.debug('got packet: %s', raw_packet)
        packet = None
        try:
            packet = decode_packet(raw_packet)
        except:
            log.exception('failed to parse packet: %s', packet)

        if packet:
            if 'ok' in packet:
                # handle response packets internally
                log.debug('command response: %s', packet)
                self._last_ack = packet
                self._command_ack.set()
            else:
                self.handle_packet(packet)
        else:
            log.warning('no valid packet')

    def handle_packet(self, packet):
        """Process incoming packet dict and optionally call callback."""
        log.debug('parsed packet: %s', packet)

        if self.packet_callback:
            # forward to callback
            self.packet_callback(packet)
        else:
            print(packet)

    def send_packet(self, fields):
        """Concat fields and send packet to gateway."""
        self.send_raw_packet(encode_packet(fields))

    def send_command(self, protocol, address, switch, action):
        """Send device command to rflink gateway."""
        command = [protocol, address, switch, action]
        log.debug('sending command: %s', command)
        self.send_packet(command)

    @asyncio.coroutine
    def send_command_ack(self, protocol, address, switch, action):
        """Send command, wait for gateway to repond with acknowledgment."""
        # serialize commands
        yield from self._ready_to_send.acquire()

        self._command_ack.clear()
        self.send_command(protocol, address, switch, action)

        log.debug('waiting for acknowledgement')
        try:
            yield from asyncio.wait_for(self._command_ack.wait(), TIMEOUT)
            log.debug('packet acknowledged')
        except concurrent.futures._base.TimeoutError:
            acknowledgement = {'ok': False, 'message': 'timeout'}
            log.warning('acknowledge timeout')
        else:
            acknowledgement = self._last_ack.get('ok', False)
        # allow next command
        self._ready_to_send.release()
        return acknowledgement


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

            task = self.send_command_ack(
                packet['protocol'],
                packet['id'],
                packet['switch'],
                cmd
            )
            self.loop.create_task(task)


class RepeaterProtocol(RflinkProtocol):
    """Repeat switch commands received."""

    def handle_packet(self, packet):
        """Handle incoming packet from rflink gateway."""
        if packet.get('switch'):
            task = self.send_command_ack(
                packet['protocol'],
                packet['id'],
                packet['switch'],
                packet['command']
            )
            self.loop.create_task(task)


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
