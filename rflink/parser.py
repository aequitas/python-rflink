"""Parsers."""

import re
from collections import defaultdict
from enum import Enum
from typing import Any, Callable, Dict, Generator, cast

UNKNOWN = 'unknown'
SWITCH_COMMAND_TEMPLATE = '{node};{protocol};{id};{switch};{command};'
PACKET_ID_SEP = '_'

# contruct regex to validate packets before parsing
DELIM = ';'
SEQUENCE = '[0-9a-zA-Z]{2}'
PROTOCOL = '[^;]{3,}'
ADDRESS = '[0-9a-zA-Z]+'
BUTTON = '[0-9a-zA-Z]+'
VALUE = '[0-9a-zA-Z]+'
COMMAND = '[0-9a-zA-Z]+'
CONTROL_COMMAND = '[A-Z]+(=[A-Z0-9]+)?'
DATA = '[a-zA-Z0-9;=_]+'
RESPONSES = 'OK'
VERSION = r'[0-9a-zA-Z\ \.-]+'

# 10;NewKaku;0cac142;3;ON;
PACKET_COMMAND = DELIM.join(['10', PROTOCOL, ADDRESS, BUTTON, COMMAND])
# 10;MiLightv1;F746;00;3c00;ON;
PACKET_COMMAND2 = DELIM.join(['10', PROTOCOL, ADDRESS, BUTTON, VALUE, COMMAND])
# 10;MERTIK;64;UP;
PACKET_COMMAND3 = DELIM.join(['10', PROTOCOL, ADDRESS, COMMAND])
# 10;DELTRONIC;001c33;
PACKET_COMMAND4 = DELIM.join(['10', PROTOCOL, ADDRESS])

# 10;REBOOT;/10;RTSRECCLEAN=9;
PACKET_CONTROL = DELIM.join(['10', CONTROL_COMMAND])

# 20;D3;OK;
PACKET_RESPONSE = DELIM.join(['20', SEQUENCE, RESPONSES])
# 20;06;NewKaku;ID=008440e6;SWITCH=a;CMD=OFF;
PACKET_DEVICE = DELIM.join(['20', SEQUENCE, PROTOCOL, DATA])
# 20;00;Nodo RadioFrequencyLink - RFLink Gateway V1.1 - R46;
PACKET_VERSION = DELIM.join(['20', SEQUENCE, VERSION])

# 11;20;0B;NewKaku;ID=000005;SWITCH=2;CMD=ON;
PACKET_DEVICE_CREATE = '11;' + PACKET_DEVICE

PACKET_HEADER_RE = '^(' + '|'.join(
    [PACKET_VERSION, PACKET_DEVICE_CREATE, PACKET_RESPONSE, PACKET_DEVICE,
     PACKET_COMMAND, PACKET_COMMAND2, PACKET_COMMAND3, PACKET_COMMAND4, PACKET_CONTROL]) + ');$'
packet_header_re = re.compile(PACKET_HEADER_RE)


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


def valid_packet(packet: str) -> bool:
    """Verify if packet is valid.

    >>> valid_packet('20;08;UPM/Esic;ID=1003;RAIN=0010;BAT=OK;')
    True
    >>> # invalid packet due to leftovers in serial buffer
    >>> valid_packet('20;00;N20;00;Nodo RadioFrequencyLink - RFLink Gateway V1.1 - R45')
    False
    """
    return bool(packet_header_re.match(packet))


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
    'Oregon UVN128/138',
    'Plieger York',
    'Byron SX',
]


class TranslationsDict(defaultdict):
    """Generate translations for Rflink protocols to serializable names."""

    def __missing__(self, key):
        """If translation does not exist yet add it and its reverse."""
        value = re.sub(r'[^a-z0-9_]+', '', key.lower())
        self[key.lower()] = value
        self[value] = key.lower()
        return value


protocol_translations = TranslationsDict(None)
[protocol_translations[protocol] for protocol in translate_protocols]


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
    >>> # unserializeable protocol name without explicit entry
    >>> # in translation table should be properly serialized
    >>> serialize_packet_id({
    ...     'protocol': 'alecto v4',
    ...     'id': '000080',
    ...     'switch': '0',
    ...     'command': 'on',
    ... })
    'alectov4_000080_0'
    """
    # translate protocol in something reversable
    protocol = protocol_translations[packet['protocol']]

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
        # lookup the reverse translation of the protocol in the translation
        # table, fallback to protocol. If this is a unserializable protocol
        # name, it has not been serialized before and is not in the
        # translate_protocols table this will result in an invalid command.
        'protocol': protocol_translations.get(protocol, protocol),
    }
    if id_switch:
        packet_identifiers['id'] = id_switch[0]
    if len(id_switch) > 1:
        packet_identifiers['switch'] = id_switch[1]

    return packet_identifiers


def packet_events(packet: dict) -> Generator:
    """Return list of all events in the packet.

    >>> x = list(packet_events({
    ...     'protocol': 'alecto v1',
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
