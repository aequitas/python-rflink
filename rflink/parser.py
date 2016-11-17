"""Parsers."""

import re
import struct

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

VALUE_TRANSLATION = {
    # 'temp': lambda t: int(t, 16)/10,
    'temp': lambda t: struct.unpack('>h', bytes.fromhex(t))[0]/10,
    'hum': int,
}

BANNER_RE = (r'(?P<hardware>[a-zA-Z\s]+) - (?P<firmware>[a-zA-Z\s]+) '
            r'V(?P<version>[0-9\.]+) - R(?P<revision>[0-9\.]+)')


def parse_packet(packet):
    """Break packet down into primitives, and do basic interpretation.

    >>> parse_packet('20;06;Kaku;ID=41;SWITCH=1;CMD=ON;') == {
    ...     'node': 'gateway',
    ...     'name': 'kaku',
    ...     'id': '41',
    ...     'switch': '1',
    ...     'command': 'on',
    ... }
    True
    """
    node_id, count, name, attrs = packet.split(';', 3)

    data = {
        'node': NODE_LOOKUP[node_id],
    }

    # make exception for version response
    if '=' in name:
        attrs = name + ';' + attrs
        name = 'version'

    # no attributes but instead the welcome banner
    if 'RFLink Gateway' in name:
        data.update(parse_banner(name))
        name = 'banner'

    if name == 'PONG':
        data['ping'] = name.lower()

    if name == 'CMD UNKNOWN':
        data['response'] = 'command unknown'
        data['ok'] = False

    if name == 'OK':
        data['ok'] = True

    data['name'] = name.lower()

    # convert key=value pairs where needed
    for attr in filter(None, attrs.strip(';').split(';')):
        key, value = attr.lower().split('=')
        if key in VALUE_TRANSLATION:
            value = VALUE_TRANSLATION.get(key)(value)
        key = ATTR_LOOKUP.get(key, key)
        data[key] = value
    return data


def parse_banner(banner):
    """Extract hardware/firmware name and version from banner."""
    return re.match(BANNER_RE, banner).groupdict()
