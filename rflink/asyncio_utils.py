"""Async helper utilities."""

import asyncio
from typing import Optional


def get_or_create_event_loop(
    loop: Optional[asyncio.AbstractEventLoop] = None,
) -> asyncio.AbstractEventLoop:
    """Get existing event loop or create a new one.

    Prefers the running loop if in async context, otherwise creates new.
    """
    if loop is not None:
        return loop
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.new_event_loop()
