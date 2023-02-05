"""Asyncio protocol implementation of RFlink."""

# ./.homeassistant/deps/lib/python/site-packages/rflink/protocol.py
# /Library/Frameworks/Python.framework/Versions/3.6//lib/python3.6/site-packages/rflink/protocol.py

import asyncio
import concurrent
import logging
from datetime import timedelta
from fnmatch import fnmatchcase
from functools import partial
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generator,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
    cast,
    overload,
)

import socket

from serial_asyncio import create_serial_connection

from .parser import (
    PacketType,
    decode_packet,
    deserialize_packet_id,
    encode_packet,
    packet_events,
    valid_packet,
)

if TYPE_CHECKING:
    from typing import Coroutine  # not available in 3.4


log = logging.getLogger(__name__)
rflink_log = None

TIMEOUT = timedelta(seconds=5)
DEFAULT_TCP_KEEPALIVE_INTERVAL = 20
DEFAULT_TCP_KEEPALIVE_COUNT = 3


class ProtocolBase(asyncio.Protocol):
    """Manage low level rflink protocol."""

    transport = None  # type: asyncio.BaseTransport
    keepalive = None  # type: Optional[int]

    def __init__(
        self,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        disconnect_callback: Optional[Callable[[Optional[Exception]], None]] = None,
        keepalive: Optional[int] = None,
        **kwargs: Any
    ) -> None:
        """Initialize class."""
        if loop:
            self.loop = loop
        else:
            self.loop = asyncio.get_event_loop()
        self.packet = ""
        self.buffer = ""
        self.packet_callback = None  # type: Optional[Callable[[PacketType], None]]
        self.disconnect_callback = disconnect_callback
        self.keepalive = keepalive

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        """Just logging for now."""
        self.transport = transport
        log.debug("connected")
        sock = transport.get_extra_info("socket")
        if self.keepalive is not None and socket is not None:
            log.debug(
                "applying TCP KEEPALIVE settings: IDLE={}/INTVL={}/CNT={}".format(
                    self.keepalive,
                    DEFAULT_TCP_KEEPALIVE_INTERVAL,
                    DEFAULT_TCP_KEEPALIVE_COUNT,
                )
            )
            if hasattr(socket, "SO_KEEPALIVE"):
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            if hasattr(socket, "TCP_KEEPIDLE"):
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, self.keepalive)
            if hasattr(socket, "TCP_KEEPINTVL"):
                sock.setsockopt(
                    socket.IPPROTO_TCP,
                    socket.TCP_KEEPINTVL,
                    DEFAULT_TCP_KEEPALIVE_INTERVAL,
                )
            if hasattr(socket, "TCP_KEEPCNT"):
                sock.setsockopt(
                    socket.IPPROTO_TCP, socket.TCP_KEEPCNT, DEFAULT_TCP_KEEPALIVE_COUNT
                )

    def data_received(self, data: bytes) -> None:
        """Add incoming data to buffer."""
        try:
            decoded_data = data.decode()
        except UnicodeDecodeError:
            invalid_data = data.decode(errors="replace")
            log.warning("Error during decode of data, invalid data: %s", invalid_data)
        else:
            log.debug("received data: %s", decoded_data.strip())
            self.buffer += decoded_data
            self.handle_lines()

    def handle_lines(self) -> None:
        """Assemble incoming data into per-line packets."""
        while "\r\n" in self.buffer:
            line, self.buffer = self.buffer.split("\r\n", 1)
            if valid_packet(line):
                self.handle_raw_packet(line)
            else:
                log.warning("dropping invalid data: %s", line)

    def handle_raw_packet(self, raw_packet: str) -> None:
        """Handle one raw incoming packet."""
        raise NotImplementedError()

    def send_raw_packet(self, packet: str) -> None:
        """Encode and put packet string onto write buffer."""
        data = packet + "\r\n"
        log.debug("writing data: %s", repr(data))
        # type ignore: transport from create_connection is documented to be
        # implementation specific bidirectional, even though typed as
        # BaseTransport
        self.transport.write(data.encode())  # type: ignore

    def log_all(self, file: Optional[str]) -> None:
        """Log all data received from RFLink to file."""
        global rflink_log
        if file is None:
            rflink_log = None
        else:
            log.debug("logging to: %s", file)
            rflink_log = open(file, "a")

    def connection_lost(self, exc: Optional[Exception]) -> None:
        """Log when connection is closed, if needed call callback."""
        if exc:
            log.exception("disconnected due to exception")
        else:
            log.info("disconnected because of close/abort.")
        if self.disconnect_callback:
            self.disconnect_callback(exc)


class PacketHandling(ProtocolBase):
    """Handle translating rflink packets to/from python primitives."""

    def __init__(
        self,
        *args: Any,
        packet_callback: Optional[Callable[[PacketType], None]] = None,
        **kwargs: Any
    ) -> None:
        """Add packethandling specific initialization.

        packet_callback: called with every complete/valid packet
        received.
        """
        super().__init__(*args, **kwargs)
        if packet_callback:
            self.packet_callback = packet_callback

    def handle_raw_packet(self, raw_packet: str) -> None:
        """Parse raw packet string into packet dict."""
        log.debug("got packet: %s", raw_packet)
        if rflink_log:
            print(raw_packet, file=rflink_log)
            rflink_log.flush()
        packet = None  # type: Optional[PacketType]
        try:
            packet = decode_packet(raw_packet)
        except BaseException:
            log.exception("failed to parse packet data: %s", raw_packet)

        log.debug("decoded packet: %s", packet)

        if packet:
            if "ok" in packet:
                # handle response packets internally
                log.debug("command response: %s", packet)
                self.handle_response_packet(packet)
            else:
                self.handle_packet(packet)
        else:
            log.warning("no valid packet")

    def handle_packet(self, packet: PacketType) -> None:
        """Process incoming packet dict and optionally call callback."""
        if self.packet_callback:
            # forward to callback
            self.packet_callback(packet)
        else:
            print("packet", packet)

    def handle_response_packet(self, packet: PacketType) -> None:
        """Handle response packet."""
        raise NotImplementedError()

    def send_packet(self, fields: PacketType) -> None:
        """Concat fields and send packet to gateway."""
        self.send_raw_packet(encode_packet(fields))

    def send_command(self, device_id: str, action: str) -> None:
        """Send device command to rflink gateway."""
        command = deserialize_packet_id(device_id)
        command["command"] = action
        log.debug("sending command: %s", command)
        self.send_packet(command)


class CommandSerialization(PacketHandling):
    """Logic for ensuring asynchronous commands are sent in order."""

    def __init__(
        self,
        *args: Any,
        packet_callback: Optional[Callable[[PacketType], None]] = None,
        **kwargs: Any
    ) -> None:
        """Add packethandling specific initialization."""
        super().__init__(*args, **kwargs)
        if packet_callback:
            self.packet_callback = packet_callback
        self._command_ack = asyncio.Event()
        self._ready_to_send = asyncio.Lock()

    def handle_response_packet(self, packet: PacketType) -> None:
        """Handle response packet."""
        self._last_ack = packet
        self._command_ack.set()

    async def send_command_ack(
        self, device_id: str, action: str
    ) -> Generator[Any, None, Optional[bool]]:
        """Send command, wait for gateway to repond with acknowledgment."""
        # serialize commands
        await self._ready_to_send.acquire()
        acknowledgement = None
        try:
            self._command_ack.clear()
            self.send_command(device_id, action)

            log.debug("waiting for acknowledgement")
            try:
                await asyncio.wait_for(self._command_ack.wait(), TIMEOUT.seconds)
                log.debug("packet acknowledged")
            except concurrent.futures._base.TimeoutError:
                acknowledgement = False
                log.warning("acknowledge timeout")
            else:
                acknowledgement = cast(bool, self._last_ack.get("ok", False))
        finally:
            # allow next command
            self._ready_to_send.release()

        return acknowledgement


class EventHandling(PacketHandling):
    """Breaks up packets into individual events with ids'.

    Most packets represent a single event (light on, measured
    temperature), but some contain multiple events (temperature and
    humidity). This class adds logic to convert packets into individual
    events each with their own id based on packet details (protocol,
    switch, etc).
    """

    def __init__(
        self,
        *args: Any,
        event_callback: Optional[Callable[[PacketType], None]] = None,
        ignore: Optional[Sequence[str]] = None,
        **kwargs: Any
    ) -> None:
        """Add eventhandling specific initialization."""
        super().__init__(*args, **kwargs)
        self.event_callback = event_callback
        # suppress printing of packets
        if not kwargs.get("packet_callback"):
            self.packet_callback = lambda x: None
        if ignore:
            log.debug("ignoring: %s", ignore)
            self.ignore = ignore
        else:
            self.ignore = []

    def _handle_packet(self, packet: PacketType) -> None:
        """Event specific packet handling logic.

        Break packet into events and fires configured event callback or
        nicely prints events for console.
        """
        events = packet_events(packet)

        for event in events:
            if self.ignore_event(event["id"]):
                log.debug("ignoring event with id: %s", event)
                continue
            log.debug("got event: %s", event)
            if self.event_callback:
                self.event_callback(event)
            else:
                self.handle_event(event)

    def handle_event(self, event: PacketType) -> None:
        """Handle of incoming event (print)."""
        string = "{id:<32} "
        if "command" in event:
            string += "{command}"
        elif "version" in event:
            if "hardware" in event:
                string += "{hardware} {firmware} "
            string += "V{version} R{revision}"
        else:
            string += "{value}"
            if event.get("unit"):
                string += " {unit}"

        print(string.format(**event))

    def handle_packet(self, packet: PacketType) -> None:
        """Apply event specific handling and pass on to packet handling."""
        self._handle_packet(packet)
        super().handle_packet(packet)

    def ignore_event(self, event_id: str) -> bool:
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
            if fnmatchcase(event_id, ignore):
                return True
        return False


class RflinkProtocol(CommandSerialization, EventHandling):
    """Combine preferred abstractions that form complete Rflink interface."""


class InverterProtocol(RflinkProtocol):
    """Invert switch commands received and send them out."""

    def handle_event(self, event: PacketType) -> None:
        """Handle incoming packet from rflink gateway."""
        if event.get("command"):
            if event["command"] == "on":
                cmd = "off"
            else:
                cmd = "on"

            task = self.send_command_ack(event["id"], cmd)
            self.loop.create_task(task)


class RepeaterProtocol(RflinkProtocol):
    """Repeat switch commands received."""

    def handle_event(self, packet: PacketType) -> None:
        """Handle incoming packet from rflink gateway."""
        if packet.get("command"):
            task = self.send_command_ack(packet["id"], packet["command"])
            self.loop.create_task(task)


@overload
def create_rflink_connection(
    port: int,
    host: str,
    baud: int = 57600,
    keepalive: Optional[int] = None,
    protocol: Type[ProtocolBase] = RflinkProtocol,
    packet_callback: Optional[Callable[[PacketType], None]] = None,
    event_callback: Optional[Callable[[PacketType], None]] = None,
    disconnect_callback: Optional[Callable[[Optional[Exception]], None]] = None,
    ignore: Optional[Sequence[str]] = None,
    loop: Optional[asyncio.AbstractEventLoop] = None,
) -> "Coroutine[Any, Any, Tuple[asyncio.BaseTransport, ProtocolBase]]":
    """Create Rflink manager class, returns transport coroutine."""
    ...


@overload
def create_rflink_connection(
    port: str,
    host: None = None,
    baud: int = 57600,
    keepalive: None = None,
    protocol: Type[ProtocolBase] = RflinkProtocol,
    packet_callback: Optional[Callable[[PacketType], None]] = None,
    event_callback: Optional[Callable[[PacketType], None]] = None,
    disconnect_callback: Optional[Callable[[Optional[Exception]], None]] = None,
    ignore: Optional[Sequence[str]] = None,
    loop: Optional[asyncio.AbstractEventLoop] = None,
) -> "Coroutine[Any, Any, Tuple[asyncio.BaseTransport, ProtocolBase]]":
    """Create Rflink manager class, returns transport coroutine."""
    ...


def create_rflink_connection(
    port: Union[None, str, int] = None,
    host: Optional[str] = None,
    baud: int = 57600,
    keepalive: Optional[int] = None,
    protocol: Type[ProtocolBase] = RflinkProtocol,
    packet_callback: Optional[Callable[[PacketType], None]] = None,
    event_callback: Optional[Callable[[PacketType], None]] = None,
    disconnect_callback: Optional[Callable[[Optional[Exception]], None]] = None,
    ignore: Optional[Sequence[str]] = None,
    loop: Optional[asyncio.AbstractEventLoop] = None,
) -> "Coroutine[Any, Any, Tuple[asyncio.BaseTransport, ProtocolBase]]":
    """Create Rflink manager class, returns transport coroutine."""
    if loop is None:
        loop = asyncio.get_event_loop()
    # use default protocol if not specified
    protocol_factory = partial(
        protocol,
        loop=loop,
        packet_callback=packet_callback,
        event_callback=event_callback,
        disconnect_callback=disconnect_callback,
        ignore=ignore if ignore else [],
        keepalive=keepalive,
    )

    # setup serial connection if no transport specified
    if host:
        conn = loop.create_connection(protocol_factory, host, cast(int, port))
    else:
        conn = create_serial_connection(loop, protocol_factory, port, baud)

    return conn  # type: ignore
