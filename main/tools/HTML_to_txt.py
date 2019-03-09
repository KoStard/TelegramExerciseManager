import sys
import os
from bs4 import BeautifulSoup
import re


# Before adding Problem models, convert HTML to intermediate text file with image references, then convert it to JSON
# <p[^>]+>\s*Reproduced[^<]+(<[^p][^>]*>[^>]+>)*[^<]*</p>\s* -> To remove reproduced... messages
# \d+ (and|to) \d+\. The answers are(\s*\d+-\w[^\d.]+)+\d+-\w\.
# Questions \d+\s(to|and)\s\d+

def convert(elem) -> str:
    res = ''
    index = 0
    if elem.name in ('ol', 'ul'):
        res += '\n!START_LIST!'
    for c in elem.contents:
        if hasattr(c, 'attrs') and 's17' in c.attrs.get('class', []):
            index = 0
        if isinstance(c, str):
            res += c
        elif c.name == 'li':
            index += 1
            resp = convert(c)
            resp = re.sub(r'((?<!\^)|^)Questions\s+(?=\d+\s+(to|and)\s+\d+)', '^Questions ', resp)
            res += f'{index}. {resp}'
            if '$' in resp:
                index = 0
            if res[-1] != '\n':
                res += '\n'
        elif c.name == 'img':
            res += f'@{c.attrs["src"].split("/")[-1]}@'
        else:
            resp = convert(c)
            if '$' in resp:
                index = 0
                res += resp
            else:
                res += resp
    if elem.name in ('ol', 'ul'):
        res += '\n!END_LIST!\n'
    if res in ('Questions', 'Answers'):
        return f'${res}'
    return (res if res[0] != '\n' else res[1:]) if res else ''


def html_to_txt(path):
    soup = BeautifulSoup(open(path, encoding='utf-8'), 'html.parser')
    res = convert(soup)
    res = re.sub(r'( {2,}|(?<=[^.!])\n(?=[a-z()+\\<>=-]|\d+\.\d+))', ' ', res)
    res = re.sub(r'\n{2,}', '\n', res)
    res = re.sub(r'(^\n|(?<![!])\n(?=[\s]))', '', res)
    res = re.sub(r'(?<=\n) ', '', res)
    res = re.sub(r'(\n\s*(\+\s*)+|\n(\+\s*){2,})', '', res)
    res = re.sub(r'’', '\'', res)
    res = re.sub(r'\s(?=\d+ (and|to) \d+\. The answers are(\s*\d+-\w[^\d.]+)+\d+-\w\.)', '\n^Answers ', res)
    res = re.sub(r'(?<=\n)(?=[^\n]+\n\$)', '#', res)
    res = re.sub(r'(?<=^)(?=[^\n]+\n\$)', '#', res)
    res = res.replace('The correct answer', 'The answer')
    open(path[:-4] + 'txt', 'w', encoding='utf-8').write(res)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        html_to_txt(sys.argv[1])
    else:
        html_to_txt('../local/PreTest-InternalMedicine/Medicine PreTest Self-Assessment and Review - 2015.html')
