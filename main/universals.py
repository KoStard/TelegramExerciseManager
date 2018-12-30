import requests
import json
import logging


def get_request(url, *, payload=None, files=None):
    if files:
        resp = requests.post(url, params=payload, files=files)
    else:
        resp = requests.get(url, params=payload)
    if resp.status_code == 200:
        return json.loads(
            resp.content.decode('utf-8'), encoding='utf-8')['result']


def configure_logging():
    """ Encoding will be utf-8 """
    root_logger = logging.getLogger()
    """ Preventing multiple calls """
    if root_logger.handlers and root_logger.handlers[
            0].stream.name == 'logs.txt' and root_logger.handlers[
                0].stream.encoding == 'utf-8':
        return
    root_logger.setLevel(logging.INFO)
    handler = logging.FileHandler('logs.txt', 'a', 'utf-8')
    root_logger.addHandler(handler)
