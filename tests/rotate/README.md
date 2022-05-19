# test rotate

## test client log rotate

1. install requirement

`pip install requests`

2. start server and client logbeat service

`python logbeat_server.py`

`python logbeat_client.py`

3. make the test

`bash tests/rotate/make_rotate.sh`

4. check the result

After about 10 secs, if 1000 items in the target table, the test is right

