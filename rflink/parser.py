"""Parsers."""

import re
from enum import Enum
from typing import Any, Callable, Dict, cast

DELIM = ';'
SWITCH_COMMAND_TEMPLATE = '{node};{protocol};{id};{switch};{command};'
PACKET_HEADER_RE = '^(10|11|20);'


class PacketHeader(Enum):
    """Packet source identification."""

    master = '10'
    echo = '11'
    gateway = '20'


PACKET_FIELDS = {
    'cmd': 'command',
    'bat': 'battery',
    'temp': 'temperature',
    'hum': 'humidity',
    'rev': 'revision',
    'ver': 'version',
}


def signed_to_float(hex: str) -> float:
    """Convert signed hexadecimal to floating value."""
    if int(hex, 16) & 0x8000:
        return -(int(hex, 16) & 0x7FFF) / 10
    else:
        return int(hex, 16) / 10


VALUE_TRANSLATION = cast(Dict[str, Callable], {
    'temp': signed_to_float,
    'hum': int,
})

BANNER_RE = (r'(?P<hardware>[a-zA-Z\s]+) - (?P<firmware>[a-zA-Z\s]+) '
             r'V(?P<version>[0-9\.]+) - R(?P<revision>[0-9\.]+)')


def is_packet_header(packet: str) -> bool:
    """Tell if string begins with packet header."""
    return bool(re.compile(PACKET_HEADER_RE).match)


def decode_packet(packet: str) -> dict:
    """Break packet down into primitives, and do basic interpretation.

    >>> decode_packet('20;06;Kaku;ID=41;SWITCH=1;CMD=ON;') == {
    ...     'node': 'gateway',
    ...     'protocol': 'kaku',
    ...     'id': '000041',
    ...     'switch': '1',
    ...     'command': 'on',
    ... }
    True
    """
    node_id, _, protocol, attrs = packet.split(DELIM, 3)

    data = cast(Dict[str, Any], {
        'node': PacketHeader(node_id).name,
    })

    # make exception for version response
    if '=' in protocol:
        attrs = protocol + DELIM + attrs
        protocol = 'version'

    # no attributes but instead the welcome banner
    elif 'RFLink Gateway' in protocol:
        data.update(parse_banner(protocol))
        protocol = 'banner'

    elif protocol == 'PONG':
        data['ping'] = protocol.lower()

    # failure response
    elif protocol == 'CMD UNKNOWN':
        data['response'] = 'command unknown'
        data['ok'] = False

    # ok response
    elif protocol == 'OK':
        data['ok'] = True

    # its a regular packet
    else:
        data['protocol'] = protocol.lower()

    # convert key=value pairs where needed
    for attr in filter(None, attrs.strip(DELIM).split(DELIM)):
        key, value = attr.lower().split('=')
        if key in VALUE_TRANSLATION:
            value = VALUE_TRANSLATION.get(key)(value)
        name = PACKET_FIELDS.get(key, key)
        data[name] = value

    # correct KaKu device address
    if data.get('protocol', '') == 'kaku' and len(data['id']) != 6:
        data['id'] = '0000' + data['id']

    return data


def parse_banner(banner: str) -> dict:
    """Extract hardware/firmware name and version from banner."""
    return re.match(BANNER_RE, banner).groupdict()


def encode_packet(packet: dict) -> str:
    """Construct packet string from packet dictionary.

    >>> encode_packet({
    ...     'protocol': 'newkaku',
    ...     'id': '000001',
    ...     'switch': '01',
    ...     'command': 'on',
    ... })
    '10;newkaku;000001;01;on;'
    """
    return SWITCH_COMMAND_TEMPLATE.format(
        node=PacketHeader.master.value,
        **packet
    )
