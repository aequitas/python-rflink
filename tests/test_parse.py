"""Test parsing of RFlink packets."""

import pytest

from rflink.parser import decode_packet


@pytest.mark.parametrize('packet,expect', [
    ['20;2D;UPM/Esic;ID=0001;TEMP=00cf;HUM=16;BAT=OK;', {
        'humidity': 16, 'temperature': 20.7,
    }],
    ['20;36;Alecto V1;ID=0334;TEMP=800d;HUM=33;BAT=OK;', {
        'temperature': -1.3
    }],
    ['20;08;UPM/Esic;ID=1003;RAIN=0010;BAT=OK;', {
        'battery': 'ok'
    }],
    ['20;46;Kaku;ID=44;SWITCH=4;CMD=OFF;', {
        'command': 'off', 'switch': '4',
    }],
    ['20;E0;NewKaku;ID=cac142;SWITCH=1;CMD=ALLOFF;', {
        'id': 'cac142', 'protocol': 'newkaku',
    }],
    ['20;00;Nodo RadioFrequencyLink - RFLink Gateway V1.1 - R45;', {
        'hardware': 'Nodo RadioFrequencyLink',
        'firmware': 'RFLink Gateway',
        'version': '1.1',
        'revision': '45',
    }],
    ['20;01;VER=1.1;REV=45;BUILD=04;', {
        'version': '1.1',
        'revision': '45',
        'build': '04',
    }],
    ['20;01;PONG;', {'ping': 'pong'}],
    [('20;02;STATUS;setRF433=ON;setNodoNRF=OFF;setMilight=OFF;'
      'setLivingColors=OFF;setAnsluta=OFF;setGPIO=OFF;setBLE=OFF;'
      'setMysensors=OFF;'), {
          'protocol': 'status',
          'setrf433': 'on',
          'setmysensors': 'off',
    }],
    ['20;01;CMD UNKNOWN;', {
        'response': 'command unknown',
        'ok': False,
    }],
    ['20;02;OK;', {
        'ok': True,
    }],
    # no actual examples available, so these are made up from protocol spec
    ['20;01;mock;ID=0;BFORECAST=1;HSTATUS=0', {
        'weather_forecast': 'sunny',
        'humidity_status': 'normal',
    }],
])
def test_packet_parsing(packet, expect):
    """Packet should be broken up into their primitives."""
    result = decode_packet(packet)

    for key, value in expect.items():
        assert result[key] == value
