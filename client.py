#!/usr/bin/env python3
import asyncio
import os
import signal

import websockets
from dotenv import dotenv_values

import utils


async def send_log(queue):
    uri = "ws://" + config['WS_USER'] + ':' + config['WS_PASS'] + '@' + config['WS_HOST'] + ':' + config['WS_PORT']
    async for websocket in websockets.connect(uri):
        try:
            log = await queue.get()
            await websocket.send(log)
            queue.task_done()
        except websockets.ConnectionClosed:
            continue


async def watch_log(queue):
    while True:
        line = log_fp.readline()
        if line:
            await queue.put(line)
        else:
            await asyncio.sleep(1)


async def client():
    queue = asyncio.Queue()
    loop = asyncio.get_running_loop()
    watch_task = asyncio.create_task(watch_log(queue))
    send_task = asyncio.create_task(send_log(queue))
    stop = loop.create_future()
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)
    await stop
    await queue.join()
    watch_task.cancel()
    send_task.cancel()

if __name__ == '__main__':
    '''
    scan log to queue, then send log
    '''
    config = dotenv_values()
    logger = utils.init_logger(config['LOG_FILE'])
    with open(config['WATCH_LOG']) as log_fp:
        log_size = os.stat(config['WATCH_LOG'])[6]
        log_fp.seek(log_size)
        asyncio.run(client())
