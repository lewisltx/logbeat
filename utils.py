#!/usr/bin/env python
import logging
from logging import handlers


def init_logger(log_file):
    logger_instance = logging.getLogger()
    if log_file:
        formatter = logging.Formatter('%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s')
        log_handler = handlers.RotatingFileHandler(log_file, maxBytes=1024 * 1024 * 50, backupCount=9,
                                                   encoding='utf8')
        log_handler.setFormatter(formatter)
        logger_instance.addHandler(log_handler)
    return logger_instance
