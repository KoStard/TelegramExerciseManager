import requests
import json
import logging
import urllib


def get_response(url, *, payload=None, files=None, use_post=False):
    """ Will get response with get/post based on files existance """
    headers = {"Content-Type": "application/json"}
    if files or use_post:
        resp = requests.post(url, params=payload, files=files)
    else:
        resp = requests.get(url, params=payload)
    if resp.status_code == 200:
        res = json.loads(resp.content.decode("utf-8"), encoding="utf-8")
        return res.get("result") if res.get("result") != None else res
    else:
        # print(resp.__dict__)
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
