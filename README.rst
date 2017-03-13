Python RFlink library
=====================

.. image:: https://travis-ci.org/aequitas/python-rflink.svg?branch=master
    :target: https://travis-ci.org/aequitas/python-rflink

.. image:: https://img.shields.io/pypi/v/rflink.svg
    :target: https://pypi.python.org/pypi/rflink

.. image:: https://img.shields.io/pypi/pyversions/rflink.svg
    :target: https://pypi.python.org/pypi/rflink

.. image:: https://img.shields.io/codeclimate/github/aequitas/python-rflink.svg
    :target: https://codeclimate.com/github/aequitas/python-rflink/code

.. image:: https://img.shields.io/codeclimate/coverage/github/aequitas/python-rflink.svg
    :target: https://codeclimate.com/github/aequitas/python-rflink/coverage

.. image:: https://img.shields.io/requires/github/aequitas/python-rflink.svg
    :target: https://requires.io/github/aequitas/python-rflink/requirements/

Library and CLI tools for interacting with RFlink 433MHz transceiver.

http://www.nemcon.nl/blog2/

Requirements
------------

- Python 3.4 (or higher)

Description
-----------

This package is created as a library for the Home assistant Rflink component implementation. A CLI has been created mainly for debugging purposes but may be extended in the future for more real-world application if needed.

Installation
------------

.. code-block:: bash

    $ pip install rflink

Usage
-----

.. code-block:: bash

    $ rflink -h
    Command line interface for rflink library.

    Usage:
      rflink [-v | -vv] [options]
      rflink [-v | -vv] [options] [--repeat <repeat>] (on | off | allon | alloff) <id>
      rflink (-h | --help)
      rflink --version

    Options:
      -p --port=<port>   Serial port to connect to [default: /dev/ttyACM0],
                           or TCP port in TCP mode.
      --baud=<baud>      Serial baud rate [default: 57600].
      --host=<host>      TCP mode, connect to host instead of serial port.
      --repeat=<repeat>  How often to repeat a command [default: 1].
      -m=<handling>      How to handle incoming packets [default: event].
      --ignore=<ignore>  List of device ids to ignore, end with * to match wildcard.
      -h --help          Show this screen.
      -v                 Increase verbosity
      --version          Show version.

Intercept and display Rflink packets:

.. code-block:: bash

    $ rflink
    rflink                           Nodo RadioFrequencyLink RFLink Gateway V1.1 R45
    newkaku_00000001_4               off
    newkaku_00000001_3               on
    alectov1_0334_temp               7.4 °C
    alectov1_0334_bat                low
    alectov1_0334_hum                26 %

Turn a device on or off:

.. code-block:: bash

    $ rflink on newkaku_0000_1
    $ rflink off newkaku_0000_1

Use of TCP mode instead of serial port (eg: ESP8266 serial bridge):

.. code-block:: bash

    $ rflink --host 1.2.3.4 --port 1234

Debug logging is shown in verbose mode for debugging:

.. code-block:: bash

    $ rflink -vv
    DEBUG:asyncio:Using selector: EpollSelector
    DEBUG:rflink.protocol:connected
    DEBUG:rflink.protocol:received data: 20;00;Nodo RadioFrequen
    DEBUG:rflink.protocol:received data: cyLink - RFLink Gateway
    DEBUG:rflink.protocol:received data: V1.1 - R45;
    DEBUG:rflink.protocol:got packet: 20;00;Nodo RadioFrequencyLink - RFLink Gateway V1.1 - R45;
    DEBUG:rflink.protocol:decoded packet: {'revision': '45', 'node': 'gateway', 'version': '1.1', 'protocol': 'unknown', 'firmware': 'RFLink Gateway', 'hardware': 'Nodo RadioFrequencyLink'}
    DEBUG:rflink.protocol:got event: {'version': '1.1', 'revision': '45', 'firmware': 'RFLink Gateway', 'hardware': 'Nodo RadioFrequencyLink', 'id': 'rflink'}
    rflink                           Nodo RadioFrequencyLink RFLink Gateway V1.1 R45
    DEBUG:rflink.protocol:received data: 2
    DEBUG:rflink.protocol:received data: 0;01;NewKaku;ID=00000001
    DEBUG:rflink.protocol:received data: ;SWITCH=4;CMD=OFF;
    DEBUG:rflink.protocol:got packet: 20;01;NewKaku;ID=00000001;SWITCH=4;CMD=OFF;
    DEBUG:rflink.protocol:decoded packet: {'id': '00000001', 'protocol': 'newkaku', 'command': 'off', 'switch': '4', 'node': 'gateway'}
    DEBUG:rflink.protocol:got event: {'id': 'newkaku_00000001_4', 'command': 'off'}
    newkaku_00000001_4               off
