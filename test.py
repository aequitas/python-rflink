import asyncio
import logging

import rflink.manager

logging.basicConfig(level=logging.DEBUG)

loop = asyncio.get_event_loop()

m = rflink.manager.Rflink(url='tty.rflink', loop=loop)
loop.create_task(m.run())
# loop.run_until_complete(m.transport)
loop.run_forever()
