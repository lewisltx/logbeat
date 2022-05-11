#!/usr/bin/env python3
import asyncio
import signal

import websockets
from dotenv import dotenv_values

import utils


async def handle_msg(message):
    pass


async def client():
    uri = "ws://" + config['WS_USER'] + ':' + config['WS_PASS'] + '@' + config['WS_HOST'] + ':' + config['WS_PORT']
    async with websockets.connect(uri) as websocket:
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(
            signal.SIGTERM, loop.create_task, websocket.close())


        # async for message in websocket:
        #     await handle_msg(message)
        # greeting = await websocket.recv()


if __name__ == '__main__':
    '''
    1. connect websocket server
    2. register log file modify event
    3. send new log to server
    '''
    config = dotenv_values()
    logger = utils.init_logger(config['LOG_FILE'])
    asyncio.run(client())
