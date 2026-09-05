#!/usr/bin/env python3
# Author: @m8sec
# License: GPLv3
import re
import argparse
import math
import os
import requests
from sys import exit
from csv import DictReader
from collections import Counter
from pathlib import Path
from crosslinked.quality import normalize_name, review, write_review
from crosslinked import utils
from crosslinked.logger import *
from crosslinked.search import CrossLinked
from crosslinked.searxng import SearXNG, search_endpoint


def banner():

    VERSION = 'v0.3.0'

    print(r'''
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
    s.add_argument('--searxng-url', default=os.environ.get('SEARXNG_URL'), help='SearXNG instance URL (or SEARXNG_URL environment variable)')
    s.add_argument('--max-pages', type=int, default=5, help='Maximum SearXNG pages (Default=5)')
    s.add_argument('--request-timeout', type=float, default=30, help='SearXNG request timeout, capped by remaining search budget (Default=30)')
    s.add_argument('--retries', type=int, default=2, help='Retries for transient SearXNG connection/502/503/504 failures (0-3, Default=2)')
    s.add_argument('--searxng-engines', type=lambda value: [v.strip() for v in value.split(',') if v.strip()], help='Comma-separated SearXNG engine names, e.g. google,bing')
    s.add_argument('--cache-dir', help='Save SearXNG response pages in this directory')
    s.add_argument('--resume', action='store_true', help='Reuse saved complete pages; retry partial pages (requires --cache-dir)')

    o = args.add_argument_group("Output arguments")
    o.add_argument('-f', dest='nformat', type=str, required=True, help="Format names, ex: 'domain\\{f}{last}', '{first}.{last}@domain.com'")
    o.add_argument('-o', dest='outfile', type=str, default='names', help='Change name of output file (omit_extension)')
    o.add_argument('--organization', help='Organization to classify against when reading an existing CSV')
    o.add_argument('--org-alias', action='append', default=[], help='Additional exact organization name accepted (repeatable)')
    o.add_argument('--exclude-org', action='append', default=[], help='Conflicting organization name to flag (repeatable)')
    o.add_argument('--include-uncertain', action='store_true', help='Include uncertain affiliations in TXT; review CSV always retains all records')

    p = args.add_argument_group("Proxy arguments")
    pr = p.add_mutually_exclusive_group(required=False)
    pr.add_argument('--proxy', dest='proxy', action='append', default=[], help='Proxy requests (IP:Port)')
    pr.add_argument('--proxy-file', dest='proxy', default=False, type=lambda x: utils.file_exists(x), help='Load proxies from file for rotation')
    parsed = args.parse_args()
    if not parsed.company_name:
        args.error('company_name is required')
    if parsed.resume and not parsed.cache_dir:
        args.error('--resume requires --cache-dir')
    if not 0 <= parsed.retries <= 3:
        args.error('--retries must be between 0 and 3')
    if not math.isfinite(parsed.request_timeout) or parsed.request_timeout <= 0:
        args.error('--request-timeout must be positive and finite')
    if parsed.searxng_engines == []:
        args.error('--searxng-engines must include at least one engine name')
    if parsed.organization is not None and not parsed.organization.strip():
        args.error('--organization cannot be blank')
    if parsed.company_name.endswith('.csv'):
        source = Path(parsed.company_name).resolve()
        for suffix in ('.txt', '.review.csv'):
            if source == Path(parsed.outfile + suffix).resolve():
                args.error('Output must not overwrite input CSV')
    if any(engine not in ('google', 'bing', 'searxng') for engine in parsed.engine) or not parsed.engine:
        args.error('--search supports google, bing, searxng')
    if not math.isfinite(parsed.timeout) or parsed.timeout <= 0 or not math.isfinite(parsed.jitter) or parsed.jitter < 0 or parsed.max_pages < 1:
        args.error('timeout and max-pages must be positive; jitter must be nonnegative')
    if 'searxng' in parsed.engine and not parsed.company_name.endswith('.csv'):
        if not parsed.searxng_url:
            args.error('--search searxng requires --searxng-url or SEARXNG_URL')
        try:
            search_endpoint(parsed.searxng_url)
        except ValueError as exc:
            args.error(str(exc))
    return parsed


def start_scrape(args):
    tmp = []
    Log.info("Searching {} for candidate profiles associated with \"{}\"".format(', '.join(args.engine), args.company_name))

    for search_engine in args.engine:
        if search_engine == 'searxng':
            c = SearXNG(args.company_name, args.searxng_url, args.timeout,
                        args.jitter, args.max_pages, args.proxy, args.searxng_engines,
                        args.cache_dir, args.resume, args.request_timeout, args.retries)
            try:
                c.validate_engines()
            except (ValueError, requests.RequestException) as exc:
                Log.warn('SearXNG engine validation failed: {}'.format(exc))
                args.search_failed = True
                continue
            tmp += c.search()
            if c.status in ('failed', 'partial'):
                args.search_failed = True
            continue
        c = CrossLinked(search_engine,  args.company_name, args.timeout, 3, args.proxy, args.jitter)
        if search_engine in c.url.keys():
            tmp += c.search()
    return tmp


def start_parse(args):
    tmp = []
    utils.file_exists(args.company_name, contents=False)
    Log.info('Reading candidate evidence from \"{}\"'.format(args.company_name))

    with open(args.company_name, 'r', encoding='utf-8-sig', newline='') as f:
        csv_data = DictReader(f)
        if not csv_data.fieldnames or not ({'Name'} <= set(csv_data.fieldnames) or {'name'} <= set(csv_data.fieldnames)):
            raise ValueError('CSV requires a Name or name column')
        for r in csv_data:
            name = r.get('Name') or r.get('original_name') or r.get('name')
            if name:
                tmp.append({'name': name.strip(), 'title': r.get('Title', r.get('title', '')) or '',
                            'text': r.get('rawText', r.get('text', '')) or '',
                            'url': r.get('URL', r.get('url', '')) or '',
                            'observed_at': r.get('Datetime', r.get('observed_at', '')) or '',
                            'snippet': r.get('snippet', '') or '', 'engines': r.get('engines', '') or ''})
    return tmp


def format_names(args, data, logger):
    tmp = []
    Log.info('{} names collected'.format(len(data)))

    for d in data:
        cleaned = normalize_name(d['name'])
        if not cleaned:
            continue
        name = nformatter(args.nformat, cleaned)
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
        parsing = args.company_name.endswith('.csv')
        if not parsing:
            setup_file_logger(args.outfile+".csv", log_name="cLinked_csv", file_mode='a')
        data = start_parse(args) if parsing else start_scrape(args)
        organization = args.organization if parsing else args.company_name
        if organization:
            reviewed = review(data, organization, args.org_alias, args.exclude_org)
            write_review(args.outfile + '.review.csv', reviewed)
            Log.info('Classification: ' + str(dict(Counter(r['classification'] for r in reviewed))))
            allowed = {'current_staff_candidate', 'current_student_candidate'}
            if args.include_uncertain:
                allowed.add('uncertain')
            data = [r for r in reviewed if r['classification'] in allowed and not r['name_issue']]
            Log.info('All evidence saved to {}.review.csv; current affiliation is not verified'.format(args.outfile))
        elif parsing:
            Log.warn('Reformatting only: use --organization to classify affiliations')
        if data:
            format_names(args, data, txt)
        elif not getattr(args, 'search_failed', False):
            Log.warn('No eligible results for TXT output')
        if getattr(args, 'search_failed', False):
            Log.warn('Search incomplete; any saved results may be partial')
            exit(1)
    except KeyboardInterrupt:
        Log.warn("Key event detected, closing...")
        exit(0)


if __name__ == '__main__':
    main()

