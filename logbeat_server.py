#!/usr/bin/env python3
import asyncio
import json
import logging
import signal
import time
from hashlib import sha256

import aiomysql
import websockets
from dotenv import dotenv_values

import utils

existed_tables = []
lock = asyncio.Lock()


async def log_insert(pool, row):
    if not isinstance(row, dict):
        return False
    row_month = row['time'][0:7].replace('-', '')
    row_table = config['DB_PREFIX'] + row_month
    if row_table not in existed_tables:
        async with lock:
            if row_table not in existed_tables:
                created_table = await create_table(pool, row_month)
                existed_tables.append(created_table)
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            sql = "INSERT INTO " + row_table + "(time, host, client_ip, request_uri, request_query, request_version, " \
                                               "request_method, status, size, upstream_time, upstream_addr, " \
                                               "upstream_status, upstream_response_time, request_time, " \
                                               "connection_time, http_referer, user_agent, x_forwarded_for, " \
                                               "sess_tag) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, " \
                                               "%s, %s, %s, %s, %s, %s)"
            await cursor.execute(sql, tuple(row.values()))
        await conn.commit()


def read_create_sql():
    with open('create_table.template') as f:
        return "".join(f.readlines())


async def create_table(pool, month=None):
    if month is None:
        month = time.strftime('%Y%m')
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            table_name = config['DB_PREFIX'] + month
            sql_content = read_create_sql()
            sql = sql_content.format(table_name)
            await cursor.execute(sql)
        await conn.commit()
        return table_name


def parse_log(message):
    """
    {"@timestamp":"2022-05-01T01:00:51+08:00","http_host":"xxx.yyy.zzz","clientip":"192.168.1.222",
    "request":"POST /index.php?id=324 HTTP/1.1","status":"200","size":"44","upstream_addr":"127.0.0.1:9000",
    "upstream_status":"200","upstream_response_time":"0.041","request_time":"0.041",
    "http_referer":"","http_user_agent":"python-requests/2.26.0","http_x_forwarded_for":""}
    """
    try:
        raw_json = json.loads(message)
    except Exception as e:
        logging.warning(repr(e), exc_info=True)
        return None
    request_arr = raw_json['request'].split(' ')
    request_uri = request_arr[1].split('?')
    upstream_time = float(raw_json['time']) - float(raw_json['request_time'].replace('-', '0'))
    parsed = {}
    parsed['time'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(raw_json['time']))) + raw_json['time'][-4:]
    parsed['host'] = raw_json['http_host']
    parsed['client_ip'] = raw_json['clientip']
    parsed['request_uri'] = request_uri[0][0:191]
    parsed['request_query'] = '' if len(request_uri) == 1 else request_uri[1][0:191]
    parsed['request_version'] = request_arr[2].split('/')[1]
    parsed['request_method'] = request_arr[0]
    parsed['status'] = raw_json['status'].replace('-', '0')
    parsed['size'] = raw_json['size'].replace('-', '0')
    parsed['upstream_time'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(upstream_time)) + ('%.3f' % upstream_time)[-4:]
    parsed['upstream_addr'] = raw_json['upstream_addr']
    parsed['upstream_status'] = empty2int(raw_json['upstream_status'].replace('-', '0'))
    parsed['upstream_response_time'] = empty2int(raw_json['upstream_response_time'].replace('-', '0'))
    parsed['request_time'] = raw_json['request_time'].replace('-', '0')
    parsed['connection_time'] = raw_json['connection_time']
    parsed['http_referer'] = raw_json['http_referer'][0:191]
    parsed['user_agent'] = raw_json['http_user_agent'][0:191]
    parsed['x_forwarded_for'] = raw_json['http_x_forwarded_for'][0:191]
    parsed['sess_tag'] = '' if 'oks_studious_robot' not in raw_json or len(raw_json['oks_studious_robot']) == 0 else \
        sha256(raw_json['oks_studious_robot'].encode('utf-8')).hexdigest()
    return parsed


def empty2int(s):
    return 0 if len(s) == 0 else s


async def msg_handler(websocket, mysql_pool):
    async for message in websocket:
        await log_insert(mysql_pool, parse_log(message))


async def init_table(pool):
    table_list = []
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            sql = "select TABLE_NAME from information_schema.TABLES where TABLE_SCHEMA=%s"
            await cursor.execute(sql, (config['DB_NAME']))
            result = await cursor.fetchall()
            if result is None:
                created_table = await create_table(pool)
                if created_table:
                    table_list.append(created_table)
            else:
                for row in result:
                    table_list.append(row[0])
    return table_list


async def server():
    loop = asyncio.get_running_loop()
    stop = loop.create_future()
    mysql_pool = await aiomysql.create_pool(host=config['DB_HOST'], port=int(config['DB_PORT']),
                                            user=config['DB_USER'], password=config['DB_PASS'],
                                            db=config['DB_NAME'], loop=loop)
    existed_tables.extend(await init_table(mysql_pool))
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
    utils.init_logger(config['LOG_FILE'], config['LOG_LEVEL'])
    asyncio.run(server())
