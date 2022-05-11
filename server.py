#!/usr/bin/env python3
import asyncio
import signal

import pymysql
import websockets
from dotenv import dotenv_values

import utils


async def mysql_insert(row):
    pass
    # async with mysql_conn.cursor() as cursor:
    #     sql = "INSERT INTO `article` (time, title, author, content) " \
    #           "VALUES (%s, %s, %s, %s)"
    #     await cursor.execute(sql, (0, row['title'], row['author'], row['content']))
    # await mysql_conn.commit()


def parse_msg(message):
    return message


async def msg_handler(websocket):
    async for message in websocket:
        await mysql_insert(parse_msg(message))


async def server():
    loop = asyncio.get_running_loop()
    stop = loop.create_future()
    loop.add_signal_handler(signal.SIGINT, stop.set_result, None)

    # TODO: support wss
    async with websockets.serve(msg_handler, config['WS_HOST'], config['WS_PORT'],
                                create_protocol=websockets.basic_auth_protocol_factory(
                                        realm="auth", credentials=(config['WS_USER'], config['WS_PASS'])
                                )):
        await stop


if __name__ == '__main__':
    '''
    1. start websocket service
    2. insert received logs into mysql
    '''
    config = dotenv_values()
    logger = utils.init_logger(config['LOG_FILE'])
    mysql_conn = pymysql.connect(host=config['DB_HOST'], port=int(config['DB_PORT']), db=config['DB_NAME'],
                                 user=config['DB_USER'], password=config['DB_PASS'],
                                 cursorclass=pymysql.cursors.DictCursor)
    asyncio.run(server())
