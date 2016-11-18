"""Manager for Rflink gateway/devices."""

from functools import partial

from serial_asyncio import create_serial_connection

from .protocol import RflinkProtocol


class Rflink:
    """Managed communication with Rflink gateway."""

    def __init__(self, *args, **kwargs):
        """Setup the manager."""
        loop = kwargs.pop('loop', None)

        # use default protocol in not specified
        protocol = kwargs.pop('protocol', partial(RflinkProtocol, loop))

        # setup serial connection if no transport specified
        self. transport = kwargs.pop('transport', create_serial_connection(
            loop, protocol, *args, **kwargs
        ))
