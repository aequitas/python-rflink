Python RFlink library
=====================

.. image:: https://github.com/aequitas/python-rflink/workflows/Push/badge.svg
    :target: https://github.com/aequitas/python-rflink/actions?query=workflow%3APush

.. image:: https://img.shields.io/pypi/v/rflink.svg
    :target: https://pypi.python.org/pypi/rflink

.. image:: https://img.shields.io/pypi/pyversions/rflink.svg
    :target: https://pypi.python.org/pypi/rflink

.. image:: https://api.codeclimate.com/v1/badges/a99a88d28ad37a79dbf6/maintainability
    :target: https://codeclimate.com/github/codeclimate/codeclimate/maintainability
    :alt: Maintainability

.. image:: https://api.codeclimate.com/v1/badges/a99a88d28ad37a79dbf6/test_coverage
   :target: https://codeclimate.com/github/codeclimate/codeclimate/test_coverage
   :alt: Test Coverage

.. image:: https://img.shields.io/requires/github/aequitas/python-rflink.svg
    :target: https://requires.io/github/aequitas/python-rflink/requirements/

.. image:: https://img.shields.io/badge/Cyberveiligheid-97%25-yellow.svg
    :target: https://eurocyber.nl

Library and CLI tools for interacting with RFlink 433MHz transceiver.

https://www.rflink.nl/

Requirements
------------

- Python 3.6 (or higher)

Description
-----------

This package is created mainly as a library for the Home assistant Rflink component implementation. A CLI has been created mainly for debugging purposes but may be extended in the future for more real-world application if needed.

The package also provides a CLI utility which allows a single RFLink hardware to be shared by multiple clients, e.g. Home assistant + Domoticz or multiple Home assistant instances.

Installation
------------

.. code-block:: bash

    $ pip install rflink

Usage of RFLink debug CLI
-------------------------

.. code-block::

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
      --ignore=<ignore>  List of device ids to ignore, wildcards supported.
      -h --help          Show this screen.
      -v                 Increase verbosity
      --version          Show version.

Intercept and display Rflink packets:

.. code-block::

    $ rflink
    rflink                           Nodo RadioFrequencyLink RFLink Gateway V1.1 R45
    newkaku_00000001_4               off
    newkaku_00000001_3               on
    alectov1_0334_temp               7.4 °C
    alectov1_0334_bat                low
    alectov1_0334_hum                26 %

Turn a device on or off:

.. code-block::

    $ rflink on newkaku_0000_1
    $ rflink off newkaku_0000_1

Use of TCP mode instead of serial port (eg: ESP8266 serial bridge):

.. code-block::

    $ rflink --host 1.2.3.4 --port 1234

Debug logging is shown in verbose mode for debugging:

.. code-block::

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

Usage of RFLinkProxy CLI
------------------------

.. code-block::

    $ rflinkproxy -h
    Command line interface for rflink proxy.

    Usage:
      rflinkproxy [-v | -vv] [options]
      rflinkproxy (-h | --help)
      rflinkproxy --version

    Options:
      --listenport=<port>  Port to listen on
      --port=<port>        Serial port to connect to [default: /dev/ttyACM0],
                             or TCP port in TCP mode.
      --baud=<baud>        Serial baud rate [default: 57600].
      --host=<host>        TCP mode, connect to host instead of serial port.
      --repeat=<repeat>    How often to repeat a command [default: 1].
      -h --help            Show this screen.
      -v                   Increase verbosity
      --version            Show version.

Share RFLink connected to serial port /dev/ttyACM1,
the proxy will listen on port 2345:

.. code-block::

    $ rflink --port /dev/ttyACM0 --listenport 2345

Share TCP mode RFLink instead of serial port (eg: ESP8266 serial bridge),
the proxy will listen on port 2345:

.. code-block::

    $ rflink --host 1.2.3.4 --port 1234 --listenport 2345

Debug logging is shown in verbose mode for debugging:

.. code-block::

    $ rflink -vv --host 1.2.3.4 --port 1234 --listenport 2345
    DEBUG:asyncio:Using selector: EpollSelector
    INFO:rflinkproxy.__main__:Serving on ('0.0.0.0', 2345)
    INFO:rflinkproxy.__main__:Initiating Rflink connection
    DEBUG:rflink.protocol:connected
    INFO:rflinkproxy.__main__:Connected to Rflink
    INFO:rflinkproxy.__main__:Incoming connection from: ::1:63293
    DEBUG:rflinkproxy.__main__:got packet: 20;00;Xiron;ID=4001;TEMP=00f1;HUM=38;BAT=LOW;
    DEBUG:rflinkproxy.__main__:decoded packet: {'node': 'gateway', 'protocol': 'xiron', 'id': '4001', 'temperature': 24.1, 'temperature_unit': '°C', 'humidity': 38, 'humidity_unit': '%', 'battery': 'low'}
    INFO:rflinkproxy.__main__:forwarding packet 20;00;Xiron;ID=4001;TEMP=00f1;HUM=38;BAT=LOW; to clients
    DEBUG:rflinkproxy.__main__:got packet: 20;00;NewKaku;ID=013373f6;SWITCH=10;CMD=ON;
    DEBUG:rflinkproxy.__main__:decoded packet: {'node': 'gateway', 'protocol': 'newkaku', 'id': '013373f6', 'switch': '10', 'command': 'on'}
    INFO:rflinkproxy.__main__:forwarding packet 20;00;NewKaku;ID=013373f6;SWITCH=10;CMD=ON; to clients
    DEBUG:rflinkproxy.__main__:got packet: 20;00;Auriol V2;ID=D101;TEMP=006f;BAT=OK;
    DEBUG:rflinkproxy.__main__:decoded packet: {'node': 'gateway', 'protocol': 'auriol v2', 'id': 'd101', 'temperature': 11.1, 'temperature_unit': '°C', 'battery': 'ok'}
    INFO:rflinkproxy.__main__:forwarding packet 20;00;Auriol V2;ID=D101;TEMP=006f;BAT=OK; to clients
