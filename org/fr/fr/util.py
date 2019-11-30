from urllib import parse
import pathlib
import tempfile

import requests


def _parse_user_agent_url(url):
    return requests.get(url).strip().split('\n')


def get_user_agent_list(brws):
    # Taken from https://github.com/tamimibrahim17/List-of-user-agents
    url_template = 'https://raw.githubusercontent.com/tamimibrahim17/List-of-user-agents/master/{}.txt'
    ual = []
    for brw in brws:
        url = url_template.format(parse.quote(brw))
        uas = [
            ua
            for ua in _parse_user_agent_url(url)[:-2]
            if "user agents string" not in ua
        ]
        ual.extend(uas)
    tempfile.NamedTemporaryFile()
    return ual


def get_proxy_list(urls=None, files=None):
    proxies = [p for p_list in map(_parse_user_agent_url, urls) for p in p_list]
    proxies.extend([
        pathlib.Path(f).read_text(encoding='utf-8') for f in files
    ])
    return proxies
