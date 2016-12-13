"""Parsers."""

import re
from enum import Enum
from typing import Any, Callable, Dict, cast

DELIM = ';'
SWITCH_COMMAND_TEMPLATE = '{node};{protocol};{id};{switch};{command};'

PACKET_COMMAND = '10;[^;]+;[a-zA-Z0-9]+;'
PACKET_OK = '^20;[0-9A-Z]{2};OK'
PACKET_DEVICE = '20;[0-9A-Z]{2};[^;]+;'
PACKET_DEVICE_CREATE = '^11;' + PACKET_DEVICE
PACKET_DEVICE_RECEIVE = '^' + PACKET_DEVICE
PACKET_HEADER_RE = '|'.join(
    [PACKET_DEVICE_CREATE, PACKET_OK, PACKET_DEVICE_RECEIVE, PACKET_COMMAND])


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
    """Tell if string begins with packet header.

    >>> is_packet_header('20;3B;NewKaku;')
    True
    >>> is_packet_header('10;Kaku;000a1;')
    True
    >>> is_packet_header('11;20;0B;NewKaku;')
    True
    >>> is_packet_header('20;93;Alecto V1;')
    True
    >>> is_packet_header('20;08;UPM/Esic;ID=1003;RAIN=0010;BAT=OK;')
    True

    """
    return bool(re.match(PACKET_HEADER_RE, packet))


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
