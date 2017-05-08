"""Asyncio protocol implementation of RFlink."""
import asyncio
import concurrent
import logging
from datetime import timedelta
from functools import partial
from typing import Callable, List

from serial_asyncio import create_serial_connection

from .parser import (
    decode_packet,
    deserialize_packet_id,
    encode_packet,
    packet_events,
    valid_packet
)

log = logging.getLogger(__name__)

TIMEOUT = timedelta(seconds=5)


class ProtocolBase(asyncio.Protocol):
    """Manage low level rflink protocol."""

    transport = None  # type: asyncio.Transport

    def __init__(self, loop=None, disconnect_callback=None) -> None:
        """Initialize class."""
        if loop:
            self.loop = loop
        else:
            self.loop = asyncio.get_event_loop()
        self.packet = ''
        self.buffer = ''
        self.disconnect_callback = disconnect_callback

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
            if valid_packet(line):
                self.handle_raw_packet(line)
            else:
                log.warning('dropping invalid data: %s', line)

    def handle_raw_packet(self, raw_packet: bytes) -> None:
        """Handle one raw incoming packet."""
        raise NotImplementedError()

    def send_raw_packet(self, packet: str):
        """Encode and put packet string onto write buffer."""
        data = packet + '\r\n'
        log.debug('writing data: %s', repr(data))
        self.transport.write(data.encode())

    def connection_lost(self, exc):
        """Log when connection is closed, if needed call callback."""
        if exc:
            log.exception('disconnected due to exception')
        else:
            log.info('disconnected because of close/abort.')
        if self.disconnect_callback:
            self.disconnect_callback(exc)


class PacketHandling(ProtocolBase):
    """Handle translating rflink packets to/from python primitives."""

    def __init__(self, *args, packet_callback: Callable = None,
                 **kwargs) -> None:
        """Add packethandling specific initialization.

        packet_callback: called with every complete/valid packet
        received.
        """
        super().__init__(*args, **kwargs)
        if packet_callback:
            self.packet_callback = packet_callback

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
            else:
                self.handle_packet(packet)
        else:
            log.warning('no valid packet')

    def handle_packet(self, packet):
        """Process incoming packet dict and optionally call callback."""
        if self.packet_callback:
            # forward to callback
            self.packet_callback(packet)
        else:
            print('packet', packet)

    def send_packet(self, fields):
        """Concat fields and send packet to gateway."""
        self.send_raw_packet(encode_packet(fields))

    def send_command(self, device_id, action):
        """Send device command to rflink gateway."""
        command = deserialize_packet_id(device_id)
        command['command'] = action
        log.debug('sending command: %s', command)
        self.send_packet(command)


class CommandSerialization(ProtocolBase):
    """Logic for ensuring asynchronous commands are send in order."""

    def __init__(self, *args, packet_callback: Callable = None,
                 **kwargs) -> None:
        """Add packethandling specific initialization."""
        super().__init__(*args, **kwargs)
        if packet_callback:
            self.packet_callback = packet_callback
        self._command_ack = asyncio.Event(loop=self.loop)
        self._ready_to_send = asyncio.Lock(loop=self.loop)

    @asyncio.coroutine
    def send_command_ack(self, device_id, action):
        """Send command, wait for gateway to repond with acknowledgment."""
        # serialize commands
        yield from self._ready_to_send.acquire()
        acknowledgement = None
        try:
            self._command_ack.clear()
            self.send_command(device_id, action)

            log.debug('waiting for acknowledgement')
            try:
                yield from asyncio.wait_for(self._command_ack.wait(),
                                            TIMEOUT.seconds, loop=self.loop)
                log.debug('packet acknowledged')
            except concurrent.futures._base.TimeoutError:
                acknowledgement = {'ok': False, 'message': 'timeout'}
                log.warning('acknowledge timeout')
            else:
                acknowledgement = self._last_ack.get('ok', False)
        finally:
            # allow next command
            self._ready_to_send.release()

        return acknowledgement


class EventHandling(PacketHandling):
    """Breaks up packets into individual events with ids'.

    Most packets represent a single event (light on, measured
    temparature), but some contain multiple events (temperature and
    humidity). This class adds logic to convert packets into individual
    events each with their own id based on packet details (protocol,
    switch, etc).
    """

    def __init__(self, *args, event_callback: Callable = None,
                 ignore: List[str] = None, **kwargs) -> None:
        """Add eventhandling specific initialization."""
        super().__init__(*args, **kwargs)
        self.event_callback = event_callback
        # suppress printing of packets
        if not kwargs.get('packet_callback'):
            self.packet_callback = lambda x: None
        if ignore:
            log.debug('ignoring: %s', ignore)
            self.ignore = ignore
        else:
            self.ignore = []

    def _handle_packet(self, packet):
        """Event specific packet handling logic.

        Break packet into events and fires configured event callback or
        nicely prints events for console.
        """
        events = packet_events(packet)

        for event in events:
            if self.ignore_event(event['id']):
                log.debug('ignoring event with id: %s', event)
                continue
            log.debug('got event: %s', event)
            if self.event_callback:
                self.event_callback(event)
            else:
                self.handle_event(event)

    def handle_event(self, event):
        """Default handling of incoming event (print)."""
        string = '{id:<32} '
        if 'command' in event:
            string += '{command}'
        elif 'version' in event:
            if 'hardware' in event:
                string += '{hardware} {firmware} '
            string += 'V{version} R{revision}'
        else:
            string += '{value}'
            if event.get('unit'):
                string += ' {unit}'

        print(string.format(**event))

    def handle_packet(self, packet):
        """Apply event specific handling and pass on to packet handling."""
        self._handle_packet(packet)
        super().handle_packet(packet)

    def ignore_event(self, event_id):
        """Verify event id against list of events to ignore.

        >>> e = EventHandling(ignore=[
        ...   'test1_00',
        ...   'test2_*',
        ... ])
        >>> e.ignore_event('test1_00')
        True
        >>> e.ignore_event('test2_00')
        True
        >>> e.ignore_event('test3_00')
        False
        """
        for ignore in self.ignore:
            if (ignore == event_id or
                    (ignore.endswith('*') and event_id.startswith(ignore[:-1]))):
                return True
        return False


class RflinkProtocol(CommandSerialization, EventHandling):
    """Combine preferred abstractions that form complete Rflink interface."""


class InverterProtocol(RflinkProtocol):
    """Invert switch commands received and send them out."""

    def handle_event(self, event):
        """Handle incoming packet from rflink gateway."""
        if event.get('command'):
            if event['command'] == 'on':
                cmd = 'off'
            else:
                cmd = 'on'

            task = self.send_command_ack(event['id'], cmd)
            self.loop.create_task(task)


class RepeaterProtocol(RflinkProtocol):
    """Repeat switch commands received."""

    def handle_event(self, packet):
        """Handle incoming packet from rflink gateway."""
        if packet.get('command'):
            task = self.send_command_ack(packet['id'], packet['command'])
            self.loop.create_task(task)


def create_rflink_connection(port=None, host=None, baud=57600, protocol=RflinkProtocol,
                             packet_callback=None, event_callback=None,
                             disconnect_callback=None, ignore=None, loop=None):
    """Create Rflink manager class, returns transport coroutine."""
    # use default protocol if not specified
    protocol = partial(
        protocol,
        loop=loop if loop else asyncio.get_event_loop(),
        packet_callback=packet_callback,
        event_callback=event_callback,
        disconnect_callback=disconnect_callback,
        ignore=ignore if ignore else [],
    )

    # setup serial connection if no transport specified
    if host:
        conn = loop.create_connection(protocol, host, port)
    else:
        baud = baud
        conn = create_serial_connection(loop, protocol, port, baud)

    return conn
