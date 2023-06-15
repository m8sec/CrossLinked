#!/usr/bin/env python3
# Author: @m8sec
# License: GPLv3
import re
import argparse
from sys import exit
from csv import reader
from crosslinked import utils
from crosslinked.logger import *
from crosslinked.search import CrossLinked


def banner():

    VERSION = 'v0.3.0'

    print('''
     _____                    _             _            _ 
    /  __ \                  | |   ({})     | |          | |
    | /  \/_ __ ___  ___ ___ | |    _ _ __ | | _____  __| |
    | |   | '__/ _ \/ __/ __|| |   | | '_ \| |/ / _ \/ _` |
    | \__/\ | | (_) \__ \__ \| |___| | | | |   <  __/ (_| | {}
     \____/_|  \___/|___/___/\_____/_|_| |_|_|\_\___|\__,_| {}

    '''.format(highlight('x', fg='gray'),
               highlight("@m8sec", fg='gray'),
               highlight(VERSION, fg='blue')))


def cli():
    args = argparse.ArgumentParser(description="", formatter_class=argparse.RawTextHelpFormatter, usage=argparse.SUPPRESS)
    args.add_argument('--debug', dest="debug", action='store_true', help=argparse.SUPPRESS)
    args.add_argument('-t', dest='timeout', type=float, default=15, help='Max timeout per search (Default=15)')
    args.add_argument('-j', dest='jitter', type=float, default=1, help='Jitter between requests (Default=1)')
    args.add_argument(dest='company_name', nargs='?', help='Target company name')

    s = args.add_argument_group("Search arguments")
    s.add_argument('--search', dest='engine', default='google,bing', type=lambda x: utils.delimiter2list(x), help='Search Engine (Default=\'google,bing\')')

    o = args.add_argument_group("Output arguments")
    o.add_argument('-f', dest='nformat', type=str, required=True, help='Format names, ex: \'domain\{f}{last}\', \'{first}.{last}@domain.com\'')
    o.add_argument('-o', dest='outfile', type=str, default='names', help='Change name of output file (omit_extension)')

    p = args.add_argument_group("Proxy arguments")
    pr = p.add_mutually_exclusive_group(required=False)
    pr.add_argument('--proxy', dest='proxy', action='append', default=[], help='Proxy requests (IP:Port)')
    pr.add_argument('--proxy-file', dest='proxy', default=False, type=lambda x: utils.file_exists(x), help='Load proxies from file for rotation')
    return args.parse_args()


def start_scrape(args):
    tmp = []
    Log.info("Searching {} for valid employee names at \"{}\"".format(', '.join(args.engine), args.company_name))

    for search_engine in args.engine:
        c = CrossLinked(search_engine,  args.company_name, args.timeout, 3, args.proxy, args.jitter)
        if search_engine in c.url.keys():
            tmp += c.search()
    return tmp


def start_parse(args):
    tmp = []
    utils.file_exists(args.company_name, contents=False)
    Log.info('Parsing employee names from \"{}\"'.format(args.company_name))

    with open(args.company_name, 'r') as f:
        csv_data = reader(f, delimiter=',')
        next(csv_data)
        for r in csv_data:
            tmp.append({'name': r[2].strip()}) if r[2] else False
    return tmp


def format_names(args, data, logger):
    tmp = []
    Log.info('{} names collected'.format(len(data)))

    for d in data:
        name = nformatter(args.nformat, d['name'])
        if name not in tmp:
            logger.info(name)
            tmp.append(name)
    Log.success("{} unique names added to {}!".format(len(tmp), args.outfile+".txt"))


def nformatter(nformat, name):
    # Get position of name values in text
    tmp = nformat.split('}')
    f_position = int(re.search(r'(-?\d+)', tmp[0]).group(0)) if ':' in tmp[0] else 0
    l_position = int(re.search(r'(-?\d+)', tmp[1]).group(0)) if ':' in tmp[1] else -1

    # Extract names from raw text
    tmp = name.split(' ')
    try:
        f_name = tmp[f_position] if len(tmp) > 2 else tmp[0]
        l_name = tmp[l_position] if len(tmp) > 2 else tmp[-1]
    except:
        f_name = tmp[0]
        l_name = tmp[-1]

    # Use replace function to create final output
    val = re.sub(r'-?\d+:', '', nformat)
    val = val.replace('{f}', f_name[0])
    val = val.replace('{first}', f_name)
    val = val.replace('{l}', l_name[0])
    val = val.replace('{last}', l_name)
    return val


def main():
    banner()
    args = cli()

    try:
        if args.debug: setup_debug_logger(); debug_args(args)                                  # Setup Debug logging
        txt = setup_file_logger(args.outfile+".txt", log_name="cLinked_txt", file_mode='w')    # names.txt overwritten
        csv = setup_file_logger(args.outfile+".csv", log_name="cLinked_csv", file_mode='a')    # names.csv appended

        data = start_parse(args) if args.company_name.endswith('.csv') else start_scrape(args)
        format_names(args, data, txt) if len(data) > 0 else Log.warn('No results found')
    except KeyboardInterrupt:
        Log.warn("Key event detected, closing...")
        exit(0)


if __name__ == '__main__':
    main()

