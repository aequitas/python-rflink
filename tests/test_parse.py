"""Test parsing of RFlink packets."""

import pytest
from rflink.parser import parse_packet


@pytest.mark.parametrize('packet,expect', [
    ['20;2D;UPM/Esic;ID=0001;TEMP=00cf;HUM=16;BAT=OK;', {
        'humidity': 16, 'temperature': 20.7,
    }],
    ['20;2D;UPM/Esic;ID=0001;TEMP=80cf;HUM=16;BAT=OK;', {
        'temperature': -3256.1,
    }],
    ['20;08;UPM/Esic;ID=1003;RAIN=0010;BAT=OK;', {
        'battery': 'ok'
    }],
    ['20;46;Kaku;ID=44;SWITCH=4;CMD=OFF;', {
        'command': 'off', 'switch': '4',
    }],
    ['20;E0;NewKaku;ID=cac142;SWITCH=1;CMD=ALLOFF;', {
        'id': 'cac142', 'name': 'newkaku',
    }],
])
def test_packet_parsing(packet, expect):
    """Packet should be broken up into their primitives."""
    result = parse_packet(packet)

    for key, value in expect.items():
        assert result[key] == value
