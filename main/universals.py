import requests
import json

def get_request(url, *, payload=None, files=None):
    if files:
        resp = requests.post(url, params=payload, files=files)
    else:
        resp = requests.get(url, params=payload)
    if resp.status_code == 200:
        return json.loads(resp.content.decode('utf-8'), encoding='utf-8')['result']
