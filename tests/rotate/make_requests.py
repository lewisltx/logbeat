import time

import requests

REQUEST_URI = 'http://localhost/phpinfo.php'

if __name__ == '__main__':
    for i in range(0, 1000):
        time.sleep(0.01)
        requests.get(REQUEST_URI)
