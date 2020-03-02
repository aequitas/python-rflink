"""Test RFlink serial low level and packet parsing protocol."""

from unittest.mock import Mock

import pytest

from rflink.protocol import EventHandling, PacketHandling

COMPLETE_PACKET = b"20;E0;NewKaku;ID=cac142;SWITCH=1;CMD=ALLOFF;\r\n"
INCOMPLETE_PART1 = b"20;E0;NewKaku;ID=cac"
INCOMPLETE_PART2 = b"142;SWITCH=1;CMD=ALLOFF;\r\n"

COMPLETE_PACKET_DICT = {
    "id": "cac142",
    "node": "gateway",
    "protocol": "newkaku",
    "command": "alloff",
    "switch": "1",
}


@pytest.fixture
def protocol(monkeypatch):
    """Rflinkprotocol instance with mocked handle_packet."""
    monkeypatch.setattr(PacketHandling, "handle_packet", Mock())
    return PacketHandling(None)


@pytest.fixture
def event_protocol(monkeypatch, ignore):
    """Rflinkprotocol instance with mocked handle_event."""
    monkeypatch.setattr(EventHandling, "handle_event", Mock())
    return EventHandling(None, ignore=ignore)


def test_complete_packet(protocol):
    """Protocol should parse and output complete incoming packets."""
    protocol.data_received(COMPLETE_PACKET)

    protocol.handle_packet.assert_called_once_with(COMPLETE_PACKET_DICT)


def test_split_packet(protocol):
    """Packet should be allowed to arrive in pieces."""
    protocol.data_received(INCOMPLETE_PART1)
    protocol.data_received(INCOMPLETE_PART2)

    protocol.handle_packet.assert_called_once_with(COMPLETE_PACKET_DICT)


def test_starting_incomplete(protocol):
    """An initial incomplete packet should be discarded."""
    protocol.data_received(INCOMPLETE_PART2)
    protocol.data_received(INCOMPLETE_PART1)
    protocol.data_received(INCOMPLETE_PART2)

    protocol.handle_packet.assert_called_once_with(COMPLETE_PACKET_DICT)


def test_multiple_packets(protocol):
    """Multiple packets should be parsed."""
    protocol.data_received(COMPLETE_PACKET)
    protocol.data_received(COMPLETE_PACKET)

    assert protocol.handle_packet.call_count == 2
    protocol.handle_packet.assert_called_with(COMPLETE_PACKET_DICT)


@pytest.mark.parametrize(
    "ignore,expected",
    [
        # Test id is newkaku_cac142_1.
        # Ignore matches:
        (["newkaku_cac142_1"], 0),
        (["newkaku_cac142_1*"], 0),
        (["newkaku_cac142_*"], 0),
        (["newkaku_cac142_?"], 0),
        (["*_cac142_*"], 0),
        (["newkaku_*_1"], 0),
        # Ignore does not match:
        (["newkaku_cac142_2"], 1),
        (["newkaku_cac142_1?"], 1),
        (["*meh?"], 1),
        ([], 1),
    ],
)
def test_ignore(event_protocol, expected):
    """Ignore should match as appropriate."""
    event_protocol.data_received(COMPLETE_PACKET)

    assert event_protocol.handle_event.call_count == expected, event_protocol.ignore
