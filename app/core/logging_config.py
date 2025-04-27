# app/core/logging_config.py
import logging

glog_filename = 'script_log.log'

logging.basicConfig(
    filename=glog_filename,
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def log_message(message, level='INFO'):
    if level.upper() == 'INFO':
        logging.info(message)
    elif level.upper() == 'WARNING':
        logging.warning(message)
    elif level.upper() == 'ERROR':
        logging.error(message)
    elif level.upper() == 'DEBUG':
        logging.debug(message)
    else:
        logging.info(message)

