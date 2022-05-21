# log-beat

日志收集程序，C/S架构，类似filebeat

## requirement

python 3.7+

MySQL 5.7+

## deploy

```shell
useradd -r logbeat -s /sbin/nologin -d /nonexistent
cd /usr/local
git clone https://github.com/montymthl/logbeat.git
cd logbeat
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
mkdir logs && chown logbeat.logbeat logs

cp .env.template .env
# config your own environment variables in .env

# client mast change logbeat_server.py to logbeat_client.py in logbeat.ini
cp logbeat.ini /etc/supervisor/conf.d/

supervisorctl update
supervisorctl status logbeat

# log rotate link nginx
supervisorctl signal usr1 logbeat

# safely update watch logs online (WATCH_LOG variable)
supervisorctl signal usr2 logbeat
```