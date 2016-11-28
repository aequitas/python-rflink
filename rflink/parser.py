"""Parsers."""

import re

NODE_LOOKUP = {
    '10': 'master',
    '11': 'echo',
    '20': 'gateway',
}

ATTR_LOOKUP = {
    'cmd': 'command',
    'bat': 'battery',
    'temp': 'temperature',
    'hum': 'humidity',
    'rev': 'revision',
    'ver': 'version',
}


def signed_to_float(hex):
    """Convert signed hexadecimal to floating value."""
    if int(hex, 16) & 0x8000:
        return -(int(hex, 16) & 0x7FFF)/10
    else:
        return int(hex, 16)/10


VALUE_TRANSLATION = {
    'temp': signed_to_float,
    'hum': int,
}

BANNER_RE = (r'(?P<hardware>[a-zA-Z\s]+) - (?P<firmware>[a-zA-Z\s]+) '
            r'V(?P<version>[0-9\.]+) - R(?P<revision>[0-9\.]+)')


def parse_packet(packet):
    """Break packet down into primitives, and do basic interpretation.

    >>> parse_packet('20;06;Kaku;ID=41;SWITCH=1;CMD=ON;') == {
    ...     'node': 'gateway',
    ...     'protocol': 'kaku',
    ...     'id': '000041',
    ...     'switch': '1',
    ...     'command': 'on',
    ... }
    True
    """
    node_id, _, protocol, attrs = packet.split(';', 3)

    data = {
        'node': NODE_LOOKUP[node_id],
    }

    # make exception for version response
    if '=' in protocol:
        attrs = protocol + ';' + attrs
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
    for attr in filter(None, attrs.strip(';').split(';')):
        key, value = attr.lower().split('=')
        if key in VALUE_TRANSLATION:
            value = VALUE_TRANSLATION.get(key)(value)
        key = ATTR_LOOKUP.get(key, key)
        data[key] = value

    # correct KaKu device address
    if data.get('protocol', '') == 'kaku' and len(data['id']) != 6:
        data['id'] = '0000' + data['id']

    return data


def parse_banner(banner):
    """Extract hardware/firmware name and version from banner."""
    return re.match(BANNER_RE, banner).groupdict()
