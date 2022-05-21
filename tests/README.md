# test

1. install requirement

`pip install requests`

2. start server and client logbeat service

`python logbeat_server.py &>>server.log &`

`python logbeat_client.py &>>client.log &`

3. check the variables in env.conf

4. make the test

test client rotate log:

`bash tests/rotate.sh`

test client update watch files online:

`bash tests/update_watch.sh`

5. check the result

After about 10 secs, if 1000 new items in the target table, the test is successful

## quickly make test environment

```shell
yum -y install centos-release-scl
yum -y install rh-nginx120 rh-mysql57
systemctl start rh-nginx120-nginx rh-mysql57-mysql
```