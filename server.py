#!/usr/bin/env python3
import asyncio
import json
import signal
import time

import aiomysql
import websockets
from dotenv import dotenv_values

import utils


async def log_insert(pool, row):
    global current_month
    row_month = row['time'][0:7].replace('-', '')
    if row_month != current_month:
        current_month = row_month
        await create_table(pool)
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            table_name = config['DB_PREFIX'] + row_month
            sql = "INSERT INTO " + table_name + " (time, host, client_ip, request, request_version, request_method," \
                                                 "status, size, upstream_addr, upstream_status, upstream_response_time," \
                                                 "request_time, http_referer, user_agent, x_forwarded_for) " \
                  "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            await cursor.execute(sql, tuple(row.values()))
        await conn.commit()


def read_create_sql():
    with open('create_table.template') as f:
        return "" . join(f.readlines())


async def create_table(pool):
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            table_name = config['DB_PREFIX'] + current_month
            sql_content = read_create_sql()
            sql = sql_content.format(table_name)
            await cursor.execute(sql)
        await conn.commit()


def parse_log(message):
    """
    {"@timestamp":"2022-05-01T01:00:51+08:00","http_host":"xxx.yyy.zzz","clinetip":"192.168.1.222",
    "request":"POST /index.php?id=324 HTTP/1.1","status":"200","size":"44","upstream_addr":"127.0.0.1:9000",
    "upstream_status":"200","upstream_response_time":"0.041","request_time":"0.041",
    "http_referer":"","http_user_agent":"python-requests/2.26.0","http_x_forwarded_for":""}
    """
    raw_json = json.loads(message)
    request_arr = raw_json['request'].split(' ')
    parsed = {}
    parsed['time'] = raw_json['@timestamp'][0:19]
    parsed['host'] = raw_json['http_host']
    parsed['client_ip'] = raw_json['clientip']
    parsed['request'] = request_arr[1].split('?')[0]
    parsed['request_version'] = request_arr[2].split('/')[1]
    parsed['request_method'] = request_arr[0]
    parsed['status'] = raw_json['status'].replace('-', '0')
    parsed['size'] = raw_json['size'].replace('-', '0')
    parsed['upstream_addr'] = raw_json['upstream_addr']
    parsed['upstream_status'] = raw_json['upstream_status'].replace('-', '0')
    parsed['upstream_response_time'] = raw_json['upstream_response_time'].replace('-', '0')
    parsed['request_time'] = raw_json['request_time'].replace('-', '0')
    parsed['http_referer'] = raw_json['http_referer'][0:191]
    parsed['user_agent'] = raw_json['http_user_agent'][0:191]
    parsed['x_forwarded_for'] = raw_json['http_x_forwarded_for'][0:191]
    return parsed


async def msg_handler(websocket, mysql_pool):
    async for message in websocket:
        await log_insert(mysql_pool, parse_log(message))


async def init_table(pool):
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            sql = "select TABLE_NAME from information_schema.TABLES where TABLE_SCHEMA=%s and TABLE_NAME=%s"
            await cursor.execute(sql, (config['DB_NAME'], config['DB_PREFIX'] + current_month))
            if await cursor.fetchone() is None:
                await create_table(pool)


async def server():
    loop = asyncio.get_running_loop()
    stop = loop.create_future()
    mysql_pool = await aiomysql.create_pool(host=config['DB_HOST'], port=int(config['DB_PORT']),
                                            user=config['DB_USER'], password=config['DB_PASS'],
                                            db=config['DB_NAME'], loop=loop)
    await init_table(mysql_pool)
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)

    # TODO: support wss
    async with websockets.serve(lambda websocket: msg_handler(websocket, mysql_pool), config['WS_HOST'],
                                config['WS_PORT'], create_protocol=websockets.basic_auth_protocol_factory(
                realm="auth", credentials=(config['WS_USER'], config['WS_PASS'])
            )):
        await stop
    mysql_pool.close()
    await mysql_pool.wait_closed()


if __name__ == '__main__':
    '''
    1. start websocket service
    2. insert received logs into mysql
    '''
    config = dotenv_values()
    logger = utils.init_logger(config['LOG_FILE'])
    current_month = time.strftime('%Y%m')
    asyncio.run(server())
