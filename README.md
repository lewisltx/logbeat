# log-beat

日志收集程序，C/S架构，类似filebeat

## requirement

python 3.7+

MySQL 5.7+

## install

`pip3 install -r requirements.txt`

复制并修改配置文件

`cp .env.template .env`

## log rotate

like nginx

`kill -USR1 $(cat logbeat.pid)`

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
# 配置env略
cp logbeat.ini /etc/supervisor/conf.d/ # 客户端需要修改logbeat_server.py为logbeat_client.py
supervisorctl reread
supervisorctl start logbeat
supervisorctl status logbeat

# 切割日志，仅客户端
supervisorctl signal usr1 logbeat
```