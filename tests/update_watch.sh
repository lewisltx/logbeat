#!/bin/bash

# import the environment variables
source /usr/local/logbeat/tests/env.conf

python /usr/local/logbeat/tests/make_requests.py &
sleep 3
kill -USR2 "$(pgrep -f logbeat_client.py)"