import requests
import json
import logging
import urllib


def get_response(url, *, payload=None, files=None, use_post=False):
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
    data = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(url)
    request.get_method = lambda: method
    with urllib.request.urlopen(request, data=data) as f:
        resp = f.read()
        res = json.loads(resp.decode("utf-8"), encoding="utf-8")
        return res.get("result") if res.get("result") is not None else res


def configure_logging():
    """ Encoding will be utf-8 """
    root_logger = logging.getLogger()
    """ Preventing multiple calls """
    if (root_logger.handlers and
            root_logger.handlers[0].stream.name == "logs.txt" and
            root_logger.handlers[0].stream.encoding == "utf-8"):
        return
    root_logger.setLevel(logging.INFO)
    handler = logging.FileHandler("logs.txt", "a", "utf-8")
    root_logger.addHandler(handler)


#- Working for related objects too
def safe_getter(obj, attr):
    if not obj or not hasattr(obj, attr):
        return None
    return getattr(obj, attr)


def get_from_Model(Model, **kwargs):
    try:
        return Model.objects.get(**kwargs)
    except Model.DoesNotExist:
        return None