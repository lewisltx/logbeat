#!/usr/bin/env python3
import asyncio
import concurrent.futures
import logging
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
        except Exception:
            logging.warning('ws exception', exc_info=True)
            continue


async def add_log(queue, watch_list):
    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        while True:
            result = await loop.run_in_executor(pool, watch_log, watch_list)
            for log in result:
                await queue.put(log)


def watch_log(watch_list):
    start_time = time.time()
    result = []
    for fp in watch_list:
        while fp.readable():
            line = fp.readline()
            if line:
                result.append(line)
                if len(result) >= 20:
                    return result
            else:
                break
    if time.time() - start_time < 1:
        time.sleep(1)
    return result


# def log_rotate():
#     global watch_task, watch_list
#     watch_task.cancel()
#     close_open_files()
#     watch_list = open_files(False)
#     watch_task = asyncio.create_task(watch_log(g_queue))


async def client():
    watch_list = open_files(True)
    g_queue = asyncio.Queue()
    watch_task = asyncio.create_task(add_log(g_queue, watch_list))
    send_task = asyncio.create_task(send_log(g_queue))
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGTERM, watch_task.cancel)
    await asyncio.gather(*[watch_task, send_task], return_exceptions=True)
    await g_queue.join()
    watch_task.cancel()
    send_task.cancel()
    close_open_files(watch_list)


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
        logging.warning('open log failed: ' + repr(e))
    if len(current_list) == 0:
        logging.warning('no available watch log')
        exit(0)


def close_open_files(watch_list):
    for fp in watch_list:
        if fp.readable():
            fp.close()


if __name__ == '__main__':
    '''
    scan log to queue, then send log
    '''
    config = dotenv_values()
    utils.init_logger(config['LOG_FILE'], config['LOG_LEVEL'])
    asyncio.run(client())
