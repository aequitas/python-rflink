import asyncio
import logging

import rflink.manager

logging.basicConfig(level=logging.DEBUG)

loop = asyncio.new_event_loop()

m = rflink.manager.create_rflink_connection(
    rflink.manager.Inverter, host="hass", port="1234", loop=loop
)
loop.create_task(m())
# loop.run_until_complete(m.transport)
loop.run_forever()
