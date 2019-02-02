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
    if (root_logger.handlers and
            root_logger.handlers[0].stream.name == "logs.txt" and
            root_logger.handlers[0].stream.encoding == "utf-8"):
        return
    root_logger.setLevel(logging.INFO)
    handler = logging.FileHandler("logs.txt", "a", "utf-8")
    root_logger.addHandler(handler)


#- Working for related objects too
def safe_getter(obj, attr):
    """ Use this function to get attributes without fear of throwing exception """
    if not obj or not hasattr(obj, attr):
        return None
    return getattr(obj, attr)


def get_from_Model(Model, **kwargs):
    """ Use this function to get model without fear of throwing exception """
    try:
        return Model.objects.get(**kwargs)
    except Model.DoesNotExist:
        return None