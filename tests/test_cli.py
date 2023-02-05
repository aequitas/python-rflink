"""Basic testing for CLI."""

import asyncio

from serial_asyncio import SerialTransport

from rflink.__main__ import main


def test_spawns(monkeypatch):
    """At least test if the CLI doesn't error on load."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # setup task to stop CLI loop
    async def stop():
        """Wait and close loop."""
        await asyncio.sleep(0.1)
        loop.stop()

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
