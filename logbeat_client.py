#!/usr/bin/env python3
import asyncio
import concurrent.futures
import logging
import os
import signal
import threading
import time

import websockets
from dotenv import dotenv_values

import utils

watch_files = []
read_lock = threading.Lock()


async def send_log(queue):
    uri = "ws://" + config['WS_USER'] + ':' + config['WS_PASS'] + '@' + config['WS_HOST'] + ':' + config['WS_PORT']
    async for websocket in websockets.connect(uri):
        try:
            while websocket.open:
                log = await queue.get()
                await websocket.send(log)
                queue.task_done()
        except websockets.ConnectionClosed:
            continue
        except Exception as e:
            logging.warning(repr(e), exc_info=True)


async def add_log(queue):
    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        while True:
            result = await loop.run_in_executor(pool, watch_log)
            for log in result:
                await queue.put(log)


def watch_log():
    start_time = time.time()
    result = []
    with read_lock:
        for fp in watch_files:
            while fp.readable():
                line = fp.readline()
                if line:
                    result.append(line)
                    if len(result) >= 20:
                        return result
                else:
                    break
            else:
                logging.warning('not readable: %s', fp.name)
    if time.time() - start_time < 1:
        time.sleep(1)
    return result


def log_rotate(queue):
    with read_lock:
        finial_logs = close_open_files(True)
    open_files(False)
    if len(finial_logs) > 0:
        asyncio.create_task(add_finial_log(finial_logs, queue))


async def add_finial_log(finial_logs, queue):
    for log in finial_logs:
        await queue.put(log)


def show_info(queue, watch_task, send_task):
    logging.info(asyncio.all_tasks())
    logging.info(queue.qsize())
    for fp in watch_files:
        logging.info("%s, %s", fp.name, fp.readable())
    watch_task.print_stack()
    send_task.print_stack()


async def client():
    open_files(True)
    g_queue = asyncio.Queue(maxsize=10000)
    watch_task = asyncio.create_task(add_log(g_queue))
    send_task = asyncio.create_task(send_log(g_queue))
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGTERM, watch_task.cancel)
    loop.add_signal_handler(signal.SIGUSR1, log_rotate, g_queue)
    loop.add_signal_handler(signal.SIGUSR2, show_info, g_queue, watch_task, send_task)
    await asyncio.wait([watch_task, send_task], return_when='FIRST_EXCEPTION')
    try:
        watch_task.exception()
        send_task.exception()
    except Exception as e:
        logging.warning(repr(e), exc_info=True)
    await g_queue.join()
    watch_task.cancel()
    send_task.cancel()
    close_open_files()


def open_files(seek):
    try:
        for file in config['WATCH_LOG'].split(' '):
            log_fp = open(file, errors='ignore')
            if log_fp.readable():
                if seek:
                    log_size = os.stat(file)[6]
                    log_fp.seek(log_size)
                watch_files.append(log_fp)
    except Exception as e:
        logging.warning('open log failed: ' + repr(e))
    if len(watch_files) == 0:
        logging.warning('no available watch log')
        exit(0)


def close_open_files(read_finial=False):
    finial_lines = []
    for fp in watch_files:
        if fp.readable():
            if read_finial:
                finial_lines.extend(fp.readlines())
            fp.close()
            watch_files.remove(fp)
    return finial_lines


if __name__ == '__main__':
    '''
    scan log to queue, then send log
    '''
    config = dotenv_values()
    utils.init_logger(config['LOG_FILE'], config['LOG_LEVEL'])
    asyncio.run(client())
