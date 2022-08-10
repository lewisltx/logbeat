#!/usr/bin/env python3
import asyncio
import concurrent.futures
import json
import logging
import os
import re
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
    async for websocket in websockets.connect(uri, ping_timeout=None):
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
                log_json = parse_log(log)
                if log_json:
                    await queue.put(log_json)


def parse_log(log):
    """
    ['# User@Host: readonly[readonly] @  [192.168.8.12]  Id: 514412\n', '# Query_time: 3.265353  Lock_time: 0.000033
    Rows_sent: 0  Rows_examined: 1052915\n', 'use mysql;\n', 'SET timestamp=1660031855;\n', "select * from `users`
    where `state` = 0 order by `id` desc limit 1;\n"]
    """
    log_dict = {'type': 'mysql_slow_log'}
    connect_matches = re.match(r'^# User@Host: (\w+)\[\w+]\s*@\s*(\w*)\s*\[(.*?)]\s*Id:\s*(\d+)$', log[0])
    if connect_matches:
        connect_info = connect_matches.groups()
        log_dict['user'] = connect_info[0]
        log_dict['host'] = connect_info[2] if connect_info[1] == '' else connect_info[1]
        log_dict['query_id'] = connect_info[3]
    else:
        logging.warning(log[0])
        return False

    query_matches = re.match(r'^# Query_time: ([0-9.]+)\s*Lock_time: ([0-9.]+)\s*Rows_sent: ([0-9]+)\s*Rows_examined: '
                             r'([0-9]+)$', log[1])
    if query_matches:
        query_info = query_matches.groups()
        log_dict['query_time'] = query_info[0]
        log_dict['lock_time'] = query_info[1]
        log_dict['rows_sent'] = query_info[2]
        log_dict['rows_examined'] = query_info[3]
    else:
        logging.warning(log[1])
        return False

    timestamp_matches = re.match(r'^SET timestamp=([0-9]+);$', log[2])
    if timestamp_matches:
        log_dict['timestamp'] = timestamp_matches.group(1)
        log.remove(log[2])
    else:
        timestamp_matches = re.match(r'^SET timestamp=([0-9]+);$', log[3])
        if timestamp_matches:
            log_dict['timestamp'] = timestamp_matches.group(1)
            log.remove(log[3])
    log_dict['content'] = ''.join(log[2:])
    return json.dumps(log_dict)


def watch_log():
    """
    用User@Host分割每个慢查询，EOF或Time保存
    # Time: 220809  15:56:39
    # User@Host: readonly[readonly] @  [192.168.8.12]  Id: 514412
    # Query_time: 3.265353  Lock_time: 0.000033 Rows_sent: 0  Rows_examined: 1052915
    SET timestamp=1660031855;
    select * from `users` where `state` = 0 order by `id` desc limit 1;
    """
    def save_result(line_list, result_list):
        if len(line_list) > 0:
            result_list.append(line_list)
        return []

    start_time = time.time()
    result = []
    with read_lock:
        for fp in watch_files:
            new_log = []
            while fp.readable():
                line = fp.readline()
                if line:
                    if line.startswith(r"# Time:"):
                        new_log = save_result(new_log, result)
                    elif line.startswith(r'# User@Host:'):
                        save_result(new_log, result)
                        new_log = [line]
                    elif len(new_log) > 0:
                        new_log.append(line)
                else:
                    save_result(new_log, result)
                    break
                if len(result) >= 10 and len(new_log) == 0:
                    return result
            else:
                logging.warning('not readable: %s', fp.name)
    if time.time() - start_time < 1:
        time.sleep(1)
    return result


async def client():
    open_files()
    g_queue = asyncio.Queue(maxsize=10000)
    watch_task = asyncio.create_task(add_log(g_queue))
    send_task = asyncio.create_task(send_log(g_queue))
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGTERM, watch_task.cancel)
    try:
        await asyncio.gather(*[watch_task, send_task])
    except asyncio.CancelledError as e:
        logging.warning('service terminated: ' + repr(e))
    except Exception as e:
        logging.warning(repr(e), exc_info=True)
        watch_task.cancel()
    finally:
        await g_queue.join()
        send_task.cancel()
        close_open_files()


def open_files(seek=False, offset_dict=None):
    if offset_dict is None:
        offset_dict = {}
    try:
        offset_ino = offset_dict.keys()
        log_fp = open(config['SLOW_LOG'], errors='ignore')
        if log_fp.readable():
            if seek or len(offset_dict) > 0:
                stat = os.stat(config['SLOW_LOG'])
                if stat.st_ino in offset_ino:
                    log_fp.seek(offset_dict[stat.st_ino])
                elif seek:
                    log_fp.seek(stat[6])
            elif re.match(r'\d+', config['SLOW_LOG_OFFSET']):
                log_fp.seek(int(config['SLOW_LOG_OFFSET']))
            watch_files.append(log_fp)
    except Exception as e:
        logging.warning('open log failed: ' + repr(e))
    if len(watch_files) == 0:
        logging.warning('no available watch log')
        exit(0)


def close_open_files(read_finial=False, save_offset=False):
    finial_lines = []
    offset_dict = {}
    for fp in watch_files:
        if fp.readable():
            if read_finial:
                finial_lines.extend(fp.readlines())
            if save_offset:
                offset_dict[os.stat(fp.name).st_ino] = fp.tell()
            fp.close()
            watch_files.remove(fp)
    if save_offset:
        return offset_dict
    return finial_lines


def update_watch():
    with read_lock:
        offset_dict = close_open_files(save_offset=True)
    open_files(seek=True, offset_dict=offset_dict)


if __name__ == '__main__':
    '''
    scan log to queue, then send log
    '''
    config = dotenv_values()
    utils.init_logger(config['LOG_FILE'], config['LOG_LEVEL'])
    asyncio.run(client())
