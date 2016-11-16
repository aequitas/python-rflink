"""Parsers."""

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
}

VALUE_TRANSLATION = {
    # 'temp': lambda t: int(t, 16)/10,
    'temp': lambda t: struct.unpack('>h', bytes.fromhex(t))[0]/10,
    'hum': int,
}


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
        'name': name.lower(),
    }

    # convert key=value pairs where needed
    for attr in attrs.strip(';').split(';'):
        key, value = attr.lower().split('=')
        if key in VALUE_TRANSLATION:
            value = VALUE_TRANSLATION.get(key)(value)
        key = ATTR_LOOKUP.get(key, key)
        data[key] = value

    return data
