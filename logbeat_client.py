#!/usr/bin/env python3
import asyncio
import os
import signal
import time

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
        start_time = time.time()
        for fp in watch_list:
            while fp.readable():
                line = fp.readline()
                if line:
                    await queue.put(line)
                else:
                    break
        if time.time() - start_time < 1:
            await asyncio.sleep(1)


def log_rotate():
    global watch_task, watch_list
    watch_task.cancel()
    close_open_files()
    watch_list = open_files(False)
    watch_task = asyncio.create_task(watch_log(g_queue))


async def client():
    global watch_task, g_queue
    g_queue = asyncio.Queue()
    loop = asyncio.get_running_loop()
    watch_task = asyncio.create_task(watch_log(g_queue))
    send_task = asyncio.create_task(send_log(g_queue))
    stop = loop.create_future()
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)
    loop.add_signal_handler(signal.SIGUSR1, log_rotate)
    await stop
    watch_task.cancel()
    await g_queue.join()
    send_task.cancel()


def open_files(seek):
    current_list = []
    try:
        for file in config['WATCH_LOG'].split(' '):
            log_fp = open(file)
            if log_fp.readable():
                if seek:
                    log_size = os.stat(file)[6]
                    log_fp.seek(log_size)
                current_list.append(log_fp)
        return current_list
    except Exception as e:
        logger.warning('open log failed: ' + repr(e))
    if len(current_list) == 0:
        logger.warning('no available watch log')
        exit(0)


def close_open_files():
    for fp in watch_list:
        if fp.readable():
            fp.close()


if __name__ == '__main__':
    '''
    scan log to queue, then send log
    '''
    config = dotenv_values()
    logger = utils.init_logger(config['LOG_FILE'], config['LOG_LEVEL'])
    watch_list = open_files(True)
    watch_task = None
    g_queue = None
    asyncio.run(client())
    close_open_files()
