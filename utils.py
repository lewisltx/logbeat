#!/usr/bin/env python
import logging
import sys
from logging import handlers


def init_logger(file=None, level=None):
    logger_instance = logging.getLogger()
    formatter = logging.Formatter('%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s')
    if file:
        log_handler = handlers.RotatingFileHandler(file, maxBytes=1024 * 1024 * 50, backupCount=9, encoding='utf-8')
    else:
        log_handler = logging.StreamHandler(sys.stdout)
    log_handler.setFormatter(formatter)
    logger_instance.addHandler(log_handler)
    if isinstance(level, str) and level in ['info', 'debug', 'error', 'warning']:
        logger_instance.setLevel(getattr(logging, level.upper()))
    return logger_instance
