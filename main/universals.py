import requests
import json
import logging
import urllib
from django.core.management import call_command
import os
import sys
import platform
from main.program_settings import python
import time


def get_response(url, *, payload=None, files=None, use_post=False, raw=False, max_retries=3, timeout=None):
    """ Will get response with get/post based on files existance """
    headers = {"Content-Type": "application/json"}
    if timeout is None:
        if payload is None or 'timeout' not in payload:
            timeout = 10
        else:
            timeout = payload['timeout']*1.5 or 10
    cycle = 0
    while True:
        cycle += 1
        try:
            if files or use_post:
                resp = requests.post(url, params=payload, files=files, timeout=timeout)
            else:
                resp = requests.get(url, params=payload, timeout=timeout)
            break
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError):
            if cycle >= max_retries:
                time.sleep(2)  # Will always try to connect
                logging.info("Trying to reconnect...")
    data = resp.json()
    if resp.status_code == 200:
        if raw:
            return resp.content
        return data.get("result") if data.get("result") is not None else data
    elif data.get('error_code') == 400:
        if data.get('description') == 'Bad Request: reply message not found':
            del payload['reply_to_message_id']  # Sending the message without replying
            return get_response(url,
                                payload=payload,
                                files=files,
                                use_post=use_post,
                                raw=raw,
                                max_retries=max_retries,
                                timeout=timeout)
        elif data.get('description') == 'Bad Request: message to delete not found':
            return   # The message is already removed
    else:
        print(resp.__dict__)
        pass
    return resp


def get_response_with_urllib(url, *, payload=None, method="POST"):
    """ Will get response with post (method kwarg) using urllib
    Is working better than requests for telegraph pages """
    data = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(url)
    request.get_method = lambda: method
    with urllib.request.urlopen(request, data=data) as f:
        resp = f.read()
        res = json.loads(resp.decode("utf-8"), encoding="utf-8")
        return res.get("result") if res.get("result") is not None else res


def configure_logging():
    """ Will configure logging """
    """ Encoding will be utf-8 """
    root_logger = logging.getLogger()
    """ Preventing multiple calls """
    if (root_logger.handlers
            and root_logger.handlers[0].stream.name == "logs.txt"
            and root_logger.handlers[0].stream.encoding == "utf-8"):
        return
    root_logger.setLevel(logging.INFO)
    handler = logging.FileHandler("logs.txt", "a", "utf-8")
    root_logger.addHandler(handler)


def get_from_Model(Model, _mode='default', **kwargs):
    """ Use this function to get model without fear of throwing exception 
    _mode -> 'default', 'direct'
    """
    try:
        if _mode == 'default':
            return Model.objects.get(**kwargs)
        elif _mode == 'direct':
            return Model.get(**kwargs)
    except Model.DoesNotExist if _mode == 'default' else Exception:
        return None


def safe_getter(model: object or dict, path: str, default=None, mode='OBJECT'):
    """ Will give the result if available, otherwise will return default
     - model will be an instance or a dict in DICT mode
     - path can start with self
     - modes -> OBJECT, DICT
    """
    mode = mode.upper()
    available_modes = ('OBJECT', 'DICT')
    if mode not in available_modes:
        raise ValueError(f"Invalid mode '{mode}' in safe_getter")
    path = path.split('.')
    if path[0] == 'self':
        path = path[1:]
    current = model
    for step in path:
        if mode == 'OBJECT' and hasattr(current, step):
            current = getattr(current, step)
        elif mode == 'DICT' and step in current:
            current = current[step]
        else:
            return default
    return current


def update_and_restart():
    """
    Will run migrations and restart the program
    """
    if platform.system() == 'Windows':
        print('Can\'t restart script in Windows.')
        return -1
    call_command('migrate')  # Test
    # Restarting the script if on macOS or Linux -> has to be executable -> chmod a+x runner.py
    # Won't match new python files
    print("Migrating...")
    os.execv(sys.executable, [python, *sys.argv])
