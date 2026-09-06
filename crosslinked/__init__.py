#!/usr/bin/env python3
# Maintainer: @a7t0fwa7 (https://github.com/a7t0fwa7/CrossLinked)
# Original author: @m8sec (https://github.com/m8sec/CrossLinked)
# License: GPLv3
from __future__ import annotations

import argparse
import math
import os
import re
import sys
from pathlib import Path
from typing import List, Optional

from crosslinked import utils
from crosslinked.logger import Log, debug_args, highlight, setup_debug_logger
from crosslinked.models import Candidate, RunState, now_iso
from crosslinked.output import (RawCsvWriter, is_input_file, read_records, write_jsonl,
                                write_review, write_run_state, write_txt)
from crosslinked.provider import Provider
from crosslinked.quality import normalize_name, review
from crosslinked.search import SEARCH_URLS, CrossLinked
from crosslinked.searxng import SearXNG, search_endpoint

PROVIDERS = tuple(SEARCH_URLS) + ('searxng',)
OUTPUT_SUFFIXES = ('.txt', '.csv', '.review.csv', '.jsonl', '.run.json')


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
               highlight("@a7t0fwa7", fg='gray'),
               highlight(VERSION, fg='blue')))


def cli():
    args = argparse.ArgumentParser(description="", formatter_class=argparse.RawTextHelpFormatter, usage=argparse.SUPPRESS)
    args.add_argument('--debug', dest="debug", action='store_true', help=argparse.SUPPRESS)
    args.add_argument('-t', dest='timeout', type=float, default=15, help='Max timeout per search (Default=15)')
    args.add_argument('-j', dest='jitter', type=float, default=1, help='Jitter between requests (Default=1)')
    args.add_argument(dest='company_name', nargs='?', help='Target company name, or an existing .csv/.jsonl export to re-process')

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
    o.add_argument('--organization', help='Organization to classify against when reading an existing CSV/JSONL')
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
    parsing = is_input_file(parsed.company_name)
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
    if parsing:
        source = Path(parsed.company_name).resolve()
        if any(source == Path(parsed.outfile + suffix).resolve() for suffix in OUTPUT_SUFFIXES):
            args.error('Output must not overwrite input file')
    if any(engine not in PROVIDERS for engine in parsed.engine) or not parsed.engine:
        args.error('--search supports ' + ', '.join(PROVIDERS))
    if not math.isfinite(parsed.timeout) or parsed.timeout <= 0 or not math.isfinite(parsed.jitter) or parsed.jitter < 0 or parsed.max_pages < 1:
        args.error('timeout and max-pages must be positive; jitter must be nonnegative')
    if 'searxng' in parsed.engine and not parsing:
        if not parsed.searxng_url:
            args.error('--search searxng requires --searxng-url or SEARXNG_URL')
        try:
            search_endpoint(parsed.searxng_url)
        except ValueError as exc:
            args.error(str(exc))
    return parsed


def build_provider(name: str, args) -> Provider:
    """Construct a provider from CLI arguments. Raises ValueError for unknown names."""
    if name == 'searxng':
        return SearXNG(args.company_name, args.searxng_url, args.timeout,
                       args.jitter, args.max_pages, args.proxy, args.searxng_engines,
                       args.cache_dir, args.resume, args.request_timeout, args.retries)
    return CrossLinked(name, args.company_name, args.timeout, 3, args.proxy, args.jitter)


def start_scrape(args, run: RunState, sink=None) -> List[Candidate]:
    tmp: List[Candidate] = []
    Log.info("Searching {} for candidate profiles associated with \"{}\"".format(', '.join(args.engine), args.company_name))

    for name in args.engine:
        provider = build_provider(name, args)
        if sink:
            provider.sinks.append(sink)
        try:
            tmp += provider.run()
        finally:
            run.providers.append(provider.state)
        Log.info('{}: {} ({}); {} records'.format(provider.name, provider.status, provider.stop_reason, len(provider.results)))
    return tmp


def start_parse(args, run: RunState) -> List[Candidate]:
    utils.file_exists(args.company_name, contents=False)
    run.source = args.company_name
    Log.info('Reading candidate evidence from \"{}\"'.format(args.company_name))
    return read_records(args.company_name)


def format_names(args, data: List[Candidate]) -> List[str]:
    tmp: List[str] = []
    Log.info('{} names collected'.format(len(data)))

    for d in data:
        cleaned = normalize_name(d.name)
        if not cleaned:
            continue
        name = nformatter(args.nformat, cleaned)
        if name not in tmp:
            tmp.append(name)
    return tmp


def _position(segment: str, default: int) -> int:
    match = re.search(r'(-?\d+)', segment) if ':' in segment else None
    return int(match.group(0)) if match else default


def nformatter(nformat: str, name: str) -> str:
    # Get position of name values in text
    tmp = nformat.split('}')
    f_position = _position(tmp[0], 0)
    l_position = _position(tmp[1], -1) if len(tmp) > 1 else -1

    # Extract names from raw text
    tmp = name.split(' ')
    try:
        f_name = tmp[f_position] if len(tmp) > 2 else tmp[0]
        l_name = tmp[l_position] if len(tmp) > 2 else tmp[-1]
    except IndexError:
        f_name = tmp[0]
        l_name = tmp[-1]

    # Use replace function to create final output
    val = re.sub(r'-?\d+:', '', nformat)
    val = val.replace('{f}', f_name[0])
    val = val.replace('{first}', f_name)
    val = val.replace('{l}', l_name[0])
    val = val.replace('{last}', l_name)
    return val


def execute(args) -> RunState:
    """Run a search or parse, write every output, and return the run state."""
    parsing = is_input_file(args.company_name)
    run = RunState(target=args.company_name, mode='parse' if parsing else 'search')
    raw: Optional[RawCsvWriter] = None
    try:
        if args.debug:
            setup_debug_logger()
            debug_args(args)
        if not parsing:
            raw = RawCsvWriter(args.outfile + '.csv')   # raw evidence is appended across runs
            run.outputs['raw_csv'] = raw.path
        data = start_parse(args, run) if parsing else start_scrape(args, run, raw)
        run.candidates = len(data)
        records: List[Candidate] = data
        organization = args.organization if parsing else args.company_name
        if organization:
            run.organization = organization
            reviewed = review(data, organization, args.org_alias, args.exclude_org)
            write_review(args.outfile + '.review.csv', reviewed)
            run.outputs['review_csv'] = args.outfile + '.review.csv'
            Log.info('Classification: ' + str(run.count_classifications(reviewed)))
            allowed = {'current_staff_candidate', 'current_student_candidate'}
            if args.include_uncertain:
                allowed.add('uncertain')
            data = [r for r in reviewed if r.classification in allowed and not r.name_issue]
            records = list(reviewed)
            Log.info('All evidence saved to {}.review.csv; current affiliation is not verified'.format(args.outfile))
        elif parsing:
            Log.warn('Reformatting only: use --organization to classify affiliations')
        write_jsonl(args.outfile + '.jsonl', records)
        run.outputs['jsonl'] = args.outfile + '.jsonl'
        names = format_names(args, data) if data else []
        write_txt(args.outfile + '.txt', names)
        run.outputs['txt'] = args.outfile + '.txt'
        run.selected = len(names)
        if names:
            Log.success("{} unique names added to {}!".format(len(names), args.outfile + ".txt"))
        elif not run.exit_code:
            Log.warn('No eligible results for TXT output')
        if run.exit_code:
            Log.warn('Search incomplete; any saved results may be partial')
    except KeyboardInterrupt:
        Log.warn("Key event detected, closing...")
        run.interrupted = True
    finally:
        if raw:
            raw.close()
        run.finished_at = now_iso()
        run.outputs['run_json'] = args.outfile + '.run.json'
        write_run_state(run.outputs['run_json'], run)
    Log.info('Run status: {}; summary in {}'.format(run.status, run.outputs['run_json']))
    return run


def main():
    banner()
    args = cli()
    run = execute(args)
    sys.exit(0 if run.interrupted else run.exit_code)


if __name__ == '__main__':
    main()
