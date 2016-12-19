"""Parsers."""

import re
from enum import Enum
from typing import Any, Callable, Dict, Generator, cast

UNKNOWN = 'unknown'
DELIM = ';'
SWITCH_COMMAND_TEMPLATE = '{node};{protocol};{id};{switch};{command};'
PACKET_ID_SEP = '_'

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
    'awinsp': 'average_windspeed',
    'baro': 'barometric_pressure',
    'bat': 'battery',
    'bforecast': 'weather_forecast',
    'chime': 'doorbell_melody',
    'cmd': 'command',
    'co2': 'co2_air_quality',
    'current': 'current_phase_1',
    'current2': 'current_phase_2',
    'current3': 'current_phase_3',
    'dist': 'distance',
    'fw': 'firmware',
    'hstatus': 'humidity_status',
    'hum': 'humidity',
    'hw': 'hardware',
    'kwatt': 'kilowatt',
    'lux': 'light_intensity',
    'meter': 'meter_value',
    'rain': 'total_rain',
    'rainrate': 'rain_rate',
    'raintot': 'total_rain',
    'rev': 'revision',
    'sound': 'noise_level',
    'temp': 'temperature',
    'uv': 'uv_intensity',
    'ver': 'version',
    'volt': 'voltage',
    'watt': 'watt',
    'winchl': 'windchill',
    'windir': 'winddirection',
    'wings': 'windgusts',
    'winsp': 'windspeed',
    'wintmp': 'windtemp',
}

UNITS = {
    'awinsp': 'km/h',
    # depends on sensor
    'baro': None,
    'bat': None,
    'bforecast': None,
    'chime': None,
    'cmd': None,
    'co2': None,
    'current': 'A',
    'current2': 'A',
    'current3': 'A',
    # depends on sensor
    'dist': None,
    'fw': None,
    'hstatus': None,
    'hum': '%',
    'hw': None,
    'kwatt': 'kW',
    'lux': 'lux',
    # depends on sensor
    'meter': None,
    'rain': 'mm',
    'rainrate': 'mm',
    'raintot': 'mm',
    'rev': None,
    # unknown, might be dB?
    'sound': None,
    # might be °F, but default to something
    'temp': '°C',
    'uv': None,
    'ver': None,
    'volt': 'v',
    'watt': 'w',
    'winchl': '°C',
    'windir': '°',
    'wings': 'km/h',
    'winsp': 'km/h',
    'wintmp': '°C',
}

HSTATUS_LOOKUP = {
    '0': 'normal',
    '1': 'comfortable',
    '2': 'dry',
    '3': 'wet',
}
BFORECAST_LOOKUP = {
    '0': 'no_info',
    '1': 'sunny',
    '2': 'partly_cloudy',
    '3': 'cloudy',
    '4': 'rain',
}


def signed_to_float(hex: str) -> float:
    """Convert signed hexadecimal to floating value."""
    if int(hex, 16) & 0x8000:
        return -(int(hex, 16) & 0x7FFF) / 10
    else:
        return int(hex, 16) / 10


VALUE_TRANSLATION = cast(Dict[str, Callable], {
    'awinsp': lambda hex: int(hex, 16) / 10,
    'baro': lambda hex: int(hex, 16),
    'bforecast': lambda x: BFORECAST_LOOKUP.get(x, 'Unknown'),
    'chime': int,
    'co2': int,
    'current': int,
    'current2': int,
    'current3': int,
    'dist': int,
    'hstatus': lambda x: HSTATUS_LOOKUP.get(x, 'Unknown'),
    'hum': int,
    'kwatt': lambda hex: int(hex, 16),
    'lux': lambda hex: int(hex, 16),
    'meter': int,
    'rain': lambda hex: int(hex, 16) / 10,
    'rainrate': lambda hex: int(hex, 16) / 10,
    'raintot': lambda hex: int(hex, 16) / 10,
    'sound': int,
    'temp': signed_to_float,
    'uv': lambda hex: int(hex, 16),
    'volt': int,
    'watt': lambda hex: int(hex, 16),
    'winchl': signed_to_float,
    'windir': lambda windir: int(windir) * 22.5,
    'wings': lambda hex: int(hex, 16) / 10,
    'winsp': lambda hex: int(hex, 16) / 10,
    'wintmp': signed_to_float,
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
    data['protocol'] = UNKNOWN
    if '=' in protocol:
        attrs = protocol + DELIM + attrs

    # no attributes but instead the welcome banner
    elif 'RFLink Gateway' in protocol:
        data.update(parse_banner(protocol))

    elif protocol == 'PONG':
        data['ping'] = protocol.lower()

    # failure response
    elif protocol == 'CMD UNKNOWN':
        data['response'] = 'command_unknown'
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
        unit = UNITS.get(key, None)

        if unit:
            data[name + '_unit'] = unit

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


# create lookup table of not easy to reverse protocol names
translate_protocols = [
    'Ikea Koppla',
    'Alecto V1',
    'Alecto V2',
    'UPM/Esic',
    'Oregon TempHygro',
    'Oregon TempHygro',
    'Oregon BTHR',
    'Oregon Rain',
    'Oregon Rain2',
    'Oregon Wind',
    'Oregon Wind2',
    'Oregon UVN128/',
    'Plieger York',
    'Byron SX',
]
protocol_translations = {
    p.lower(): re.sub(r'[^a-z0-9_]+', '', p.lower()) for p in translate_protocols
}
rev_protocol_translations = {v: k for k, v in protocol_translations.items()}


def serialize_packet_id(packet: dict) -> str:
    """Serialize packet identifiers into one reversable string.

    >>> serialize_packet_id({
    ...     'protocol': 'newkaku',
    ...     'id': '000001',
    ...     'switch': '01',
    ...     'command': 'on',
    ... })
    'newkaku_000001_01'
    >>> serialize_packet_id({
    ...     'protocol': 'ikea koppla',
    ...     'id': '000080',
    ...     'switch': '0',
    ...     'command': 'on',
    ... })
    'ikeakoppla_000080_0'

    """
    # translate protocol in something reversable
    protocol = protocol_translations.get(
        packet['protocol'], packet['protocol'])

    if protocol == UNKNOWN:
        protocol = 'rflink'

    return '_'.join(filter(None, [
        protocol,
        packet.get('id', None),
        packet.get('switch', None),
    ]))


def deserialize_packet_id(packet_id: str) -> dict:
    r"""Turn a packet id into individual packet components.

    >>> deserialize_packet_id('newkaku_000001_01') == {
    ...     'protocol': 'newkaku',
    ...     'id': '000001',
    ...     'switch': '01',
    ... }
    True
    >>> deserialize_packet_id('ikeakoppla_000080_0') == {
    ...     'protocol': 'ikea koppla',
    ...     'id': '000080',
    ...     'switch': '0',
    ... }
    True
    """
    if packet_id == 'rflink':
        return {'protocol': UNKNOWN}

    protocol, *id_switch = packet_id.split(PACKET_ID_SEP)
    assert len(id_switch) < 3

    packet_identifiers = {
        'protocol': rev_protocol_translations.get(protocol, protocol),
    }
    if id_switch:
        packet_identifiers['id'] = id_switch[0]
    if len(id_switch) > 1:
        packet_identifiers['switch'] = id_switch[1]

    return packet_identifiers


def packet_events(packet: dict) -> Generator:
    """Return list of all events in the packet.

    >>> x = list(packet_events({
    ...     'protocol': 'alectov1',
    ...     'id': 'ec02',
    ...     'temperature': 1.0,
    ...     'temperature_unit': '°C',
    ...     'humidity': 10,
    ...     'humidity_unit': '%',
    ... }))
    >>> assert {
    ...     'id': 'alectov1_ec02_temp',
    ...     'sensor': 'temperature',
    ...     'value': 1.0,
    ...     'unit': '°C',
    ... } in x
    >>> assert {
    ...     'id': 'alectov1_ec02_hum',
    ...     'sensor': 'humidity',
    ...     'value': 10,
    ...     'unit': '%',
    ... } in x
    >>> y = list(packet_events({
    ...     'protocol': 'newkaku',
    ...     'id': '000001',
    ...     'switch': '01',
    ...     'command': 'on',
    ... }))
    >>> assert {'id': 'newkaku_000001_01', 'command': 'on'} in y

    """
    field_abbrev = {v: k for k, v in PACKET_FIELDS.items()}

    packet_id = serialize_packet_id(packet)
    events = {f: v for f, v in packet.items() if f in field_abbrev}
    if 'command' in events or 'version' in events:
        # switch events only have one event in each packet
        yield dict(id=packet_id, **events)
    else:
        # sensors can have multiple
        for sensor, value in events.items():
            unit = packet.get(sensor + '_unit', None)
            yield {
                'id': packet_id + PACKET_ID_SEP + field_abbrev[sensor],
                'sensor': sensor,
                'value': value,
                'unit': unit,
            }
