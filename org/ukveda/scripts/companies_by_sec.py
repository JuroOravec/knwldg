import contextlib
import csv
from datetime import datetime
from functools import reduce
import logging
from pathlib import Path
import re
import subprocess
import sys

import click

'''
Codes taken from http://resources.companieshouse.gov.uk/sic/
Data taken from http://download.companieshouse.gov.uk/en_output.html
NACE (Nomenclature des Activités économiques dans les Communautés Européennes)
https://siccode.com/page/what-is-a-nace-code
'''


logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


nace_files = ['data/uk_companies_sic.txt']
data_files = ['data/company_data_basic__2019_08_01.csv']
destinations = ['data/company_data_basic']

delimeter = '\t'
stop_char = '!'
comment_char = '#'
categ_stop_char = '\n'
nace_start_index = 26 # zero-based
nace_end_index = 30
allow_mkdir = True
debug_company_index = 0


class MultiOut(object):
    '''
    File-like object for writing to multiple outputs
    https://stackoverflow.com/a/41284244/9788634
    '''
    def __init__(self, *args):
        self.handles = args

    def write(self, s):
        for f in self.handles:
            f.write(s)

        
def escape_name(s):
    s = s.replace('&', 'and').lower()
    s = re.sub(r'\s+|\-', '_', s)
    return re.sub(r'[^a-z0-9_]', '', s)

def get_extension(s):
    return s.split('.')[-1]

def get_time_tag():
    return datetime.now().strftime('%Y_%m_%d__%H_%M_%S')

def unlink_path(p):
    logger.debug(f'Deleting file "{p.name}"')
    p.unlink()

def apply_fns(l, fns):
    l = [reduce(lambda o, fn: fn(o), fns, i) for i in l]
    return l

def format_nace(s):
    return s.zfill(5)

def first(iter):
    return list(iter)[0]

def mapl(fn, iter):
    return list(map(fn, iter))

def log_file_creation(files):
    logger.debug('Creating files: "{}"'.format(
        '", "'.join(mapl(lambda p: p.name, files))
    ))

def parse_nace(nace_paths):
    def reset_vars():
        return [-1, ''] * 2

    def parse_single_file(nace_path, env=None):
        nace = {}
        with nace_path.open() as f:
            prev_nace, prev_name, curr_nace, curr_name = reset_vars()
            env_vars = { **(env or dict()) }

            for line in f:
                if line[0] == comment_char:
                    m = re.match(f'{comment_char}\s*(\w+)\s*=\s*(\w+)', line)
                    if m is not None:
                        k, v = m.groups()
                        env_vars[k] = v
                    continue

                elif line[0] == categ_stop_char:
                    prev_nace, prev_name, curr_nace, curr_name = reset_vars()
                    env_vars.clear()
                    continue

                prev_nace, prev_name = curr_nace, curr_name
                curr_nace, curr_name = line.strip().split(delimeter)
                curr_nace = int(curr_nace)

                if prev_name == stop_char or prev_nace < 0:
                    continue

                categ = f'{escape_name(prev_name)}'
                if 'prefix' in env_vars:
                    categ = f"{env_vars.get('prefix')}_{categ}"

                nace_range = range(prev_nace, curr_nace)
                nace[categ] = nace_range
        return nace

    nace = reduce(
        lambda d, d1: {**d, **d1}, 
        mapl(parse_single_file, nace_paths), 
        dict()
    )
    return nace


def parse_data_grep(data_files, out_files, categ_range):
    time_tag = get_time_tag()
    for categ, categ_range in nace.items():
        out_filename = f'{categ}__{time_tag}{data_files[0].suffix}'
        out_files = mapl(lambda p: p.joinpath(out_filename), dest_dirs)

        escape_first_n_fields = f'(?:[^,]+,){{{nace_index},}}?.*?'
        nace_range = '|'.join(apply_fns(categ_range, [str, format_nace]))

        try:
            log_file_creation(out_files)
            with contextlib.ExitStack() as stack:
                # context managers of opened files
                out_files_cms = mapl(lambda p: p.open('w'), out_files)
                mapl(stack.enter_context, out_files_cms)
                out = MultiOut(**out_files_cms)

                base_command = ['grep','-E', f"{escape_first_n_fields}(?:{nace_range}).*?business\.data\.gov"]
                commands = [
                    [
                        *base_command,
                        str(data_file.relative_to(Path.cwd()))
                    ] for data_file in data_files
                ]

                # redirect the subprocess strout to all out_files
                for command in commands:
                    logger.debug(f'Calling command \"{" ".join(command)}\"')
                    subprocess.run(command, stdout=out)

            # Remove empty files
            for out_file in out_files:
                if not out_file.stat().st_size:
                    unlink_path(out_file)

        except BaseException as e:
            logger.error(f'Command failure: {repr(e)}')
            mapl(unlink_path, out_files)

def parse_data_python(nace, data_paths, dest_paths, suffix=None):
    header = None
    visited_categs = {}
    time_tag = get_time_tag()
    out_paths_by_categ = {}

    for categ, categ_range in nace.items():
        out_filename = f'{categ}__{time_tag}{suffix or ""}'
        out_paths = mapl(lambda p: p.joinpath(out_filename), dest_paths)
        out_paths_by_categ[categ] = out_paths

        log_file_creation(out_paths)
        mapl(lambda p: p.open('w').close(), out_paths)

    for data_path in data_paths:
        with data_path.open(newline='') as in_f:
            datareader = csv.reader(in_f)
            for datarow in datareader:
                if header is None:
                    header = datarow
                nace_vals = datarow[nace_start_index : nace_end_index]
                for categ, categ_range in nace.items():
                    categ_range = mapl(str, categ_range)

                    if any(q in s for q in categ_range for s in nace_vals):
                        with contextlib.ExitStack() as stack:
                            # context managers of opened files
                            logger.debug(f'Adding "{datarow[debug_company_index]}" to "{categ}"')
                            out_files_cms = mapl(lambda p: p.open('a', newline=''), out_paths_by_categ[categ])
                            mapl(stack.enter_context, out_files_cms)
                            # write to the target files
                            writers = mapl(csv.writer, out_files_cms)
                            if categ not in visited_categs:
                                mapl(lambda csvw: csvw.writerow(header), writers)
                                visited_categs[categ] = None
                            mapl(lambda csvw: csvw.writerow(datarow), writers)       
    # Remove empty files
    for categ in out_paths_by_categ:
        for out_file in out_paths_by_categ[categ]:
            if not out_file.stat().st_size:
                unlink_path(out_file)

@click.command()
def companies_by_sec():
    cwd = Path().cwd()
    src_paths = mapl(cwd.joinpath, nace_files)
    data_paths = mapl(cwd.joinpath, data_files)
    dest_dir_paths = mapl(cwd.joinpath, destinations)

    nace = parse_nace(src_paths)

    # create destination directories if they do not exist yet
    if allow_mkdir:
        mapl(lambda p: p.mkdir(parents=True, exist_ok=True), dest_dir_paths)

    suffix = Path(data_files[0]).suffix
    parse_data_python(nace, data_paths, dest_dir_paths, suffix)


if __name__ == '__main__':
    companies_by_sec()