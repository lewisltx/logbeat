#!/bin/bash

# import the environment variables
source /usr/local/logbeat/tests/env.conf

python /usr/local/logbeat/tests/make_requests.py &
sleep 3
mv "$MAIN_LOG" "${MAIN_LOG::-4}"-"$(date +%F-%H-%M-%S)".log
kill -USR1 "$(cat "${NGINX_PID}")"
kill -USR1 "$(pgrep -f logbeat_client.py)"