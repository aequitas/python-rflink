"""Basic testing for proxy."""

import asyncio

from rflinkproxy.__main__ import main
from serial_asyncio import SerialTransport


def test_spawns(monkeypatch):
    """At least test if the CLI doesn't error on load."""
    # setup task to stop CLI loop
    @asyncio.coroutine
    def stop():
        """Wait and close loop."""
        yield from asyncio.sleep(0.1)
        loop.stop()

    loop = asyncio.new_event_loop()
    if hasattr(asyncio, "ensure_future"):
        ensure_future = asyncio.ensure_future
    else:  # Deprecated since Python 3.4.4
        ensure_future = getattr(asyncio, "async")
    ensure_future(stop(), loop=loop)

    # use simulation interface
    args = ["--port", "loop://", "-v"]

    # patch to make 'loop://' work with serial_asyncio
    monkeypatch.setattr(SerialTransport, "_ensure_reader", lambda self: True)

    # test calling results in the loop close cleanly
    assert main(args, loop=loop) is None
