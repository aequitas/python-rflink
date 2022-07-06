"""Test parsing of RFlink packets."""

import os

import pytest

from rflink.parser import (
    PACKET_FIELDS,
    UNITS,
    VALUE_TRANSLATION,
    decode_packet,
    deserialize_packet_id,
    serialize_packet_id,
    valid_packet,
)

PROTOCOL_SAMPLES = os.path.join(os.path.dirname(__file__), "protocol_samples.txt")


@pytest.mark.parametrize(
    "packet,expect",
    [
        [
            "20;2D;UPM/Esic;ID=0001;TEMP=00cf;HUM=16;BAT=OK;",
            {"humidity": 16, "temperature": 20.7},
        ],
        [
            "20;36;Alecto V1;ID=0334;TEMP=800d;HUM=33;BAT=OK;",
            {"temperature": -1.3, "temperature_unit": "°C"},
        ],
        ["20;08;UPM/Esic;ID=1003;RAIN=0010;BAT=OK;", {"battery": "ok"}],
        ["20;46;Kaku;ID=44;SWITCH=4;CMD=OFF;", {"command": "off", "switch": "4"}],
        [
            "20;E0;NewKaku;ID=cac142;SWITCH=1;CMD=ALLOFF;",
            {"id": "cac142", "protocol": "newkaku"},
        ],
        [
            "20;00;Nodo RadioFrequencyLink - RFLink Gateway V1.1 - R45;",
            {
                "hardware": "Nodo RadioFrequencyLink",
                "firmware": "RFLink Gateway",
                "version": "1.1",
                "revision": "45",
            },
        ],
        [
            "20;01;VER=1.1;REV=45;BUILD=04;",
            {"version": "1.1", "revision": "45", "build": "04"},
        ],
        ["20;01;PONG;", {"ping": "pong"}],
        [
            (
                "20;02;STATUS;setRF433=ON;setNodoNRF=OFF;setMilight=OFF;"
                "setLivingColors=OFF;setAnsluta=OFF;setGPIO=OFF;setBLE=OFF;"
                "setMysensors=OFF;"
            ),
            {"protocol": "status", "setrf433": "on", "setmysensors": "off"},
        ],
        ["20;01;CMD UNKNOWN;", {"response": "command_unknown", "ok": False}],
        ["20;02;OK;", {"ok": True}],
        # no actual examples available, so these are made up from protocol spec
        [
            "20;01;mock;ID=0;BFORECAST=1;HSTATUS=0",
            {"weather_forecast": "sunny", "humidity_status": "normal"},
        ],
        [
            "20;00;Nodo RadioFrequencyLink - RFLink Gateway V1.1 - R45;",
            {
                "version": "1.1",
                "revision": "45",
                "hardware": "Nodo RadioFrequencyLink",
                "firmware": "RFLink Gateway",
            },
        ],
        [
            "20;05;RTS;ID=147907;SWITCH=01;CMD=UP;",
            {"id": "147907", "switch": "01", "protocol": "rts", "command": "up"},
        ],
        [
            "20;00;Internal Pullup on RF-in disabled;",
            {"message": "Internal Pullup on RF-in disabled"},
        ],
        [
            "20;9A;FA500;ID=0000db9e;SWITCH=01;CMD=SET_LEVEL=2;",
            {"command": "set_level=2"},
        ],
        [
            "20;84;Debug;RTS P1;a63f33003cf000665a5a;",
            {"rts_p1": "a63f33003cf000665a5a"},
        ],
        [
            "20;84;DEBUG;RTS P1;a63f33003cf000665a5a;",
            {"rts_p1": "a63f33003cf000665a5a"},
        ],
        ["20;01;setGPIO=ON;", {"setgpio": "on"}],
    ],
)
def test_packet_parsing(packet, expect):
    """Packet should be broken up into their primitives."""
    result = decode_packet(packet)

    for key, value in expect.items():
        assert result[key] == value

    # make sure each packet is serialized without failure
    packet_id = serialize_packet_id(result)

    # and deserialize it again
    packet_identifiers = deserialize_packet_id(packet_id)

    original = set(result.items())
    transserialized = set(packet_identifiers.items())
    assert transserialized.issubset(original)


def test_descriptions():
    """Every value translation should be paired with a description."""
    for key in VALUE_TRANSLATION:
        assert key in PACKET_FIELDS


def test_units():
    """Every description should have a unit available."""
    for key in PACKET_FIELDS:
        assert key in UNITS


@pytest.mark.parametrize(
    "packet",
    [
        line.strip()
        for line in open(PROTOCOL_SAMPLES).readlines()
        if line.strip() and line[0] != "#"
    ],
)
def test_packet_valiation(packet):
    """Verify if packet validation correctly identifies official samples.

    https://www.rflink.nl/protref.php
    """
    assert valid_packet(packet)


def test_invalid_type():
    """Packet where a value type cannot be converted to expected type should not error."""
    packet = "20;2D;RFX10METER;ID=79;TYPE=10;METER=7ef36;"

    assert decode_packet(packet) == {
        "node": "gateway",
        "protocol": "rfx10meter",
        "id": "79",
        "type": "10",
    }


@pytest.mark.parametrize("device_id", ["dooya_v4_6d5f8e00_3f"])
def test_underscored(device_id):
    """Test parsing device id's that contain underscores."""
    assert deserialize_packet_id(device_id)
