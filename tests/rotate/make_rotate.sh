#!/bin/bash

python /usr/local/logbeat/tests/rotate/make_requests.py &
sleep 3
mv /home/wwwlogs/access.log /home/wwwlogs/access-$(date +%F-%H-%M-%S).log
kill -USR1 `cat /usr/local/nginx/logs/nginx.pid`
kill -USR1 $(pgrep -f logbeat_client.py)