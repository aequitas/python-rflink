"""Test RFlink serial low level and packet parsing protocol."""

from unittest.mock import Mock

import pytest

from rflink.protocol import PacketHandling

COMPLETE_PACKET = b'20;E0;NewKaku;ID=cac142;SWITCH=1;CMD=ALLOFF;\r\n'
INCOMPLETE_PART1 = b'20;E0;NewKaku;ID=cac'
INCOMPLETE_PART2 = b'142;SWITCH=1;CMD=ALLOFF;\r\n'

COMPLETE_PACKET_DICT = {
    'id': 'cac142',
    'node': 'gateway',
    'protocol': 'newkaku',
    'command': 'alloff',
    'switch': '1',
}


@pytest.fixture
def protocol(monkeypatch):
    """Rflinkprotocol instance with mocked handle_packet."""
    monkeypatch.setattr(PacketHandling, 'handle_packet', Mock())
    return PacketHandling(None)


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
