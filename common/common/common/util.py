import unicodedata
from datetime import datetime
import functools
from http import cookies
import inspect
import importlib
import itertools
from pathlib import Path
import re
from urllib import parse
import tempfile

import requests



def string_combinations(
    seed="",
    pattern=None,
    start=None,
    end=None,
    valid_chars=None,
    variants=None,
    min_length=1,
    index=None
    ):
    '''
    Generates string combinations from `seed`, until the string is at least of `min_length`.

    Only combinations that are lexicographically equal to or after `start` and equal to
    or before `end` are returned, if `start` or `end` are given.

    If `pattern` is given, only those combinations are returned that match the pattern.
    `valid_chars` specifies which characters can be added to the `seed` string.

    If any of the valid characters can have multiple variants (such as `c` being `c` or `ch`),
    these can be specified by `variants`. `variants` must be either a list of tuples or dict.
    Keys must match characters that have multiple variants. Values must be a list of these variants.
    These variants can be of any length.

    Index specifies which character of the `seed` string is being considered. If `index` is out of range
    of `seed` string, the new character is appended to the `seed` string

    EXAMPLE:
    >>> string_combinations(
    >>>   seed="hi",
    >>>   start='ho',
    >>>   end='hq',
    >>>   variants={'o': ['oh', 'ok', 'obuh']},
    >>>   min_length=4,
    >>>   index=1
    >>> )

    # From string 'hi', generates all strings that start with 'ho' and 'hq' (inclusive) and everything in between,
    >>>
    # whereas the string combinations start at index 1 ("i"). Generated string are of length 4, possibly except when
    >>>
    # strings containing 'o' were generated variants with 'oh', 'ok', or 'obuh' instead of 'o'.
    >>>
    '''

    if index is not None \
        and len(seed) >= min_length \
            and (not(start) or seed[:len(start)] >= start)\
            and (not(end) or seed[:len(end)] <= end):
        yield seed
        return

    seed = bytearray(seed, "ascii")
    index = len(seed) if index is None else index
    valid_chars = valid_chars or 'abcdefghijklmnopqrstuvwxzy0123456789'
    # variants should be {char: [list, of, variants]} or [(char, [list, of, variants])]
    variants = variants or []
    variants = variants.items() if isinstance(variants, dict) else variants

    start_reached = False

    for s in valid_chars:
        # Skip if start is given and has not been reached yet
        # or if end is given and has been already reached
        if (start and not(start_reached) and len(start) >= (index + 1) and s != start[index]):
            continue
        # Prevent going into depth if we already have minimum length
        # and start or end conditions are shorter than that
        elif index > min_length - 1 and (start and index > len(start) - 1) and (end and index > len(end) - 1):
            continue
        if not start_reached:
            start_reached = True

        # workaround for "ch" being considered a separate char.
        # uses (temp_seed + variant) as a final name for all variants

        curr_variants = [s]
        for case, v in variants:
            if s == case:
                curr_variants.extend(v)

        for v in curr_variants:

            temp_seed = seed.copy()

            # Modify seed with current variant
            for i, c in enumerate(v):
                if len(temp_seed) < index + 1 + i:
                    temp_seed.append(ord(c))
                else:
                    temp_seed[index] = ord(c)

            temp_seed = temp_seed.decode()

            # End reached
            if end and temp_seed[:len(end)] > end:
                return

            # Skip seed if it does not match the pattern
            if pattern and not re.search(pattern, temp_seed):
                continue

            # Go one level deeper (1 char longer seed)
            results = string_combinations(
                seed=temp_seed,
                valid_chars=valid_chars,
                pattern=pattern,
                start=start,
                end=end,
                variants=variants,
                min_length=min_length,
                index=index + 1
            )
            for res in results:
                yield res


def map_dict_val(fn, d):
    return {
        k: fn(v)
        for k, v in d.items()
    }


def unpack_url(url):
    '''
    Get URL object and Query object from a url, as returned by 
    urllib.parse.urlparse and urllib.parse.parse_qs, respectively.

    Reverse of pack_url
    '''

    url_obj = parse.urlparse(url)
    q_obj = parse.parse_qs(url_obj.query)
    q_obj = map_dict_val(lambda l: l[0], q_obj)
    return url_obj, q_obj


def pack_url(url_obj, q_obj):
    '''
    Get url string from URL object and Query object.

    Reverse of unpack_url
    '''

    url_obj = url_obj._replace(query=parse.urlencode(q_obj))
    url_string = parse.urlunparse(url_obj)
    return url_string


def xpath_class(classes, operator="or"):
    ''''Format an XPath class condition'''

    return f" {operator} ".join(
        f"contains(concat(' ', normalize-space(@class),' '),' {cls} ')"
        for cls in classes
    )

def xpath_startswith(attr, s):
    return f"@{attr} and starts-with(@{attr}, '{s}')"


def get_dir(obj):
    path = inspect.getfile(obj)
    return str(Path(path).parent.absolute())


def module_from_abs_path(name, path):
    '''
    See https://stackoverflow.com/questions/67631/how-to-import-a-module-given-the-full-path
    # importing-a-source-file-directly
    and https://docs.python.org/3/library/importlib.html
    '''
    spec = importlib.util.spec_from_file_location(name, path)
    mdl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mdl)
    return mdl


def local_module(cls, filename):
    '''
    Search the directory of a module where `cls` is defined and
    look for file `filename`.

    Raises `ValueError` if the file does not exist.

    Raises `ModuleNotFoundError` if the import failed.
    '''

    cls_dir = get_dir(cls)
    file_path = Path(cls_dir, filename)
    file_abs_path = str(file_path.absolute())
    if not file_path.exists():
        raise ValueError('File not found: {}'.format(file_abs_path))
    import_path = cls.__module__.rsplit('.', 1)[0]
    module_path = "{}.{}".format(import_path, file_path.stem)
    module = module_from_abs_path(module_path, file_abs_path)
    return module


def pairwise(iterable):
    '''See https://docs.python.org/3/library/itertools.html#itertools-recipes'''
    a, b = itertools.tee(iterable)
    next(b, None)
    return itertools.zip_longest(a, b, fillvalue=object())


def remove_adjacent_dup(iterable):
    '''
    See https://stackoverflow.com/a/34986013/9788634
    '''
    return [x for x, y in pairwise(x) if x != y]


def soft_update(d1, *dicts, dict_mode='override', list_mode='override', copy=False):
    '''
    Update dictonary entries, overriding values if they are primitives
    or if the type changes.

    Returns the updated dictionary. If `copy` is `True`, the updates are made
    to a copy. 

    If the values are dictionaries then one of the following modes apply:
    - `update` - keep the nested dictionaries, and only update entries
    - `override` - replace the nested dictonaries with new values

    If the values are lists then one of the following modes apply:
    - `append` - join elements from all occurences
    - `set` - add new list member only if it is not present in the list already
    - `override` - replace the list with new value
    '''
    if copy:
        out = {}
        the_dicts = [d1, *dicts]
    else:
        out = d1
        the_dicts = dicts

    for d in the_dicts:
        for k, v in d.items():
            if k not in out:
                out[k] = v
                continue
            elif type(v) != type(out[k]):
                out[k] = v
            elif isinstance(v, dict):
                if dict_mode == 'update':
                    out[k].update(v)
                elif dict_mode == 'override':
                    out[k] = v
                else:
                    raise ValueError(f'Unknown dict mode "{dict_mode}"')
            elif isinstance(v, list):
                if list_mode == 'append':
                    out[k].extend(v)
                elif list_mode == 'set':
                    out[k].extend([i for i in v if i not in out[k]])
                elif list_mode == 'override':
                    out[k] = v
                else:
                    raise ValueError(f'Unknown list mode "{list_mode}"')
            else:
                out[k] = v
    return out


def grouper(n, iterable, fillvalue=None):
    "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return itertools.zip_longest(fillvalue=fillvalue, *args)


def flatten_json(y):
    out = {}

    def flatten(x, name=''):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + '_')
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, name + str(i) + '_')
                i += 1
        else:
            out[name[:-1]] = x
    flatten(y)
    return out


@functools.wraps(filter)
def lfilter(functionOrNone, iterable):
    return list(filter(functionOrNone, iterable))


@functools.wraps(map)
def lmap(func, *iterables):
    return list(map(func, *iterables))


@functools.wraps(map)
def map2str(*iterables):
    return map(str, iterables)


@functools.wraps(map)
def map2int(*iterables):
    return map(int, iterables)


def flatten(iterable):
    t = type(iterable)
    return t(i for grp in iterable for i in grp)

def lflatten(iterable):
    return flatten(list(iterable))

def time_tag():
    return datetime.now().strftime('%Y_%m_%d__%H_%M_%S')


def update_request_cookies(request, inplace=True, pattern=None):
    c = cookies.SimpleCookie()
    h = request.headers.copy() if not inplace else request.headers
    for header in ['Cookie', 'Set-Cookie']:
        for ck in h.getlist(header):
            c.load(ck.decode('utf-8'))
    h.pop('cookie', None)
    h.pop('set-cookie', None)
    for morsel in c.values():
        if pattern is None or re.search(pattern, morsel.key):
            h.appendlist('cookie', '{}={}'.format(morsel.key, morsel.value))
    return h


def strip_accents(text):
    '''https://stackoverflow.com/a/44433664/9788634'''
    try:
        text = unicode(text, 'utf-8')
    except NameError:  # unicode is a default on python 3
        pass
    text = unicodedata.normalize('NFD', text)\
        .encode('ascii', 'ignore')\
        .decode("utf-8")
    return str(text)


def dol2lot(dol):
    '''Convert dict of lists to list of (key, value) tuples'''
    lot = []
    for k, val in dol.items():
        try:
            vals = iter(val)
        except TypeError:
            vals = [val]
        lot.extend((k, v) for v in vals)
    return lot


def lot2dol(lot):
    '''Convert list of (key, value) tuples to dict of lists'''
    dol = {}
    for k, val in lot:
        if k not in dol:
            dol[k] = []
        dol[k].append(val)
    return dol


def conditional_deco(deco, predicate):
    '''
    Decorator that takes another decorator and a predicate,
    and applies the second decorator to a function only if the predicate 
    evaluates to True.a[@href and starts-with(@href, '/events/csv')]
    '''
    def deco_(function):
        @functools.wraps(function)
        def inner(*args, **kwargs):
            if predicate(*args, **kwargs):
                return deco(function)(*args, **kwargs)
            return function(*args, **kwargs)
        return inner
    return deco_


def is_url(url):
  try:
    result = parse.urlparse(url)
    return all([result.scheme, result.netloc])
  except ValueError:
    return False



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
        Path(f).read_text(encoding='utf-8') for f in files
    ])
    return proxies