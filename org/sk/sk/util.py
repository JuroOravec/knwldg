from urllib import request, parse
import pathlib


def parse_text_from_url(url):
    return request.urlopen(url).read().decode('utf-8').strip().split('\n')


def get_user_agent_list(brws):
    # Taken from https://github.com/tamimibrahim17/List-of-user-agents
    url_template = 'https://raw.githubusercontent.com/tamimibrahim17/List-of-user-agents/master/{}.txt'
    ual = []
    for brw in brws:
        url = url_template.format(parse.quote(brw))
        uas = parse_text_from_url(url)[:-2]
        ual.extend(uas)
    return ual


def get_proxy_list(urls=None, files=None):
    proxies = [p for p_list in map(parse_text_from_url, urls) for p in p_list]
    proxies.extend([
        pathlib.Path(f).read_text(encoding='utf-8') for f in files
    ])
    return proxies

