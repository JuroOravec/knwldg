from functools import reduce
import re
import unicodedata

import pandas as pd


# input
files = [
    'data/businesses_by_name.csv',
    'data/businesses_by_name2.csv'
]
output = 'data/joined.csv'
column_renames = {
    'obchodne meno': 'business name',
    'predmet cinnosti': 'business activity'
}

# merging input
dfs = [
    pd.read_csv(f, dtype=str)
    for f in files
]

joined = pd.concat(dfs, sort=False).fillna('')

# data transformation definitions


def apply_fns(dfs, fns, cols=None):
    '''
    Common interface for applying a list of mapping functions to DataFrame,
    Series or other objects
    '''
    if not cols:
        if isinstance(df, pd.DataFrame):
            def map_fn(o, fn): return o.applymap(fn)
        elif isinstance(df, pd.Series):
            def map_fn(o, fn): return o.map(fn)
        else:
            def map_fn(o, fn): return fn(o)
        dfs = [reduce(lambda o, fn: map_fn(o, fn), fns, df) for df in dfs]
        return dfs
    for col in cols:
        dfs = [reduce(lambda o, fn: o[col].map(fn), fns, df) for df in dfs]
    return dfs


def escape_whitespace(s):
    '''
    Remove leading and trailing whitespace and replace in-text
    whitespace with `_`
    '''
    s = s.strip()
    s = '_'.join(re.split(r'\s+', s))
    return s


def reduce_whitespace(s):
    '''
    Remove leading and trailing whitespace and reduce whitespace to a single 
    space while preserving single copy of `\\r` and `\\n` for each occurence
    in-text
    '''
    s = s.strip()
    whitespaces = re.findall(r'\s+', s)
    for whitespace in whitespaces:
        new_whitespace = ""
        new_whitespace += "\n" if "\n" in whitespace else ""
        new_whitespace += "\r" if "\r" in whitespace else ""
        new_whitespace = " " if new_whitespace == "" else new_whitespace
        s = s.replace(whitespace, new_whitespace)
    return s


def strip_accents(text):
    '''https://stackoverflow.com/a/31607735/9788634'''
    try:
        text = unicode(text, 'utf-8')
    except (TypeError, NameError):  # unicode is a default on python 3
        pass
    text = unicodedata.normalize('NFD', text)
    text = text.encode('ascii', 'ignore')
    text = text.decode("utf-8")
    return str(text)


def escape_characters(s):
    '''Remove all characters which are not alphanumeric or underscore'''
    return re.sub(r'[^a-z0-9_]', '', s)
    


# normalize and rename column names
clean_headers = lambda hs: apply_fns(
    hs, [strip_accents, str.lower, escape_whitespace, escape_characters]
)
clean_column_renames = {
    clean_headers(k)[0]: clean_headers(v)[0]
    for k, v in column_renames.items()
}

joined = joined.rename(columns={
    k: clean_column_renames.get(k_clean, k_clean)
    for k_clean in clean_headers([k])
    for k in joined.columns.tolist()
})

# data transformations
joined = apply_fns([joined], [reduce_whitespace, str.lower, strip_accents])[0]

# output
joined.to_csv(output, index=False)
