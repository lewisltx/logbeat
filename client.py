#!/usr/bin/env python3
import asyncio
import os
import signal

import pyinotify
import websockets
from dotenv import dotenv_values

import utils


class TrackModifications(pyinotify.ProcessEvent):
    def my_init(self, ws):
        self._ws_conn = ws

    def process_IN_MODIFY(self, event):
        line = log_fp.readline()
        if line:
            loop = asyncio.get_running_loop()
            loop.create_task(self._ws_conn.send(line))


async def client():
    uri = "ws://" + config['WS_USER'] + ':' + config['WS_PASS'] + '@' + config['WS_HOST'] + ':' + config['WS_PORT']
    async with websockets.connect(uri) as websocket:
        wm = pyinotify.WatchManager()
        loop = asyncio.get_running_loop()
        notifier = pyinotify.AsyncioNotifier(wm, loop, default_proc_fun=TrackModifications(ws=websocket))
        loop.add_signal_handler(signal.SIGTERM, loop.create_task, websocket.close())
        wm.add_watch(config['WATCH_LOG'], pyinotify.ALL_EVENTS)
        await asyncio.Future()


if __name__ == '__main__':
    '''
    1. register log file modify event
    2. connect websocket server
    3. send log
    '''
    config = dotenv_values()
    logger = utils.init_logger(config['LOG_FILE'])
    with open(config['WATCH_LOG']) as log_fp:
        log_size = os.stat(config['WATCH_LOG'])[6]
        log_fp.seek(log_size)
        asyncio.run(client())
