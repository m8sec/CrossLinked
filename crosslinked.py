#!/usr/bin/env python3
# Author: m8r0wn
# License: GPLv3

import logging
import argparse
from sys import exit
from bs4 import BeautifulSoup
from unidecode import unidecode

from taser import printx
from taser.logx import setup_fileLogger, setup_consoleLogger
from taser.proto.http import extract_webdomain, web_request, get_statuscode
from taser.utils import file_exists, delimiter2dict, delimiter2list, TaserTimeout

def banner():
    author = '@m8r0wn'
    version = 'v0.1.0'
    printx.colored('''
     _____                    _             _            _ 
    /  __ \                  | |   (x)     | |          | |
    | /  \/_ __ ___  ___ ___ | |    _ _ __ | | _____  __| |
    | |   | '__/ _ \/ __/ __|| |   | | '_ \| |/ / _ \/ _` |
    | \__/\ | | (_) \__ \__ \| |___| | | | |   <  __/ (_| |
     \____/_|  \___/|___/___/\_____/_|_| |_|_|\_\___|\__,_| {}
     
    {}
    '''.format(version, printx.highlight(author, fg='gray')), fg='blue')

class CrossLinked():
    URL = {'google': 'https://www.google.com/search?q=site:linkedin.com/in+"{}"&num=100&start={}',
           'bing': 'http://www.bing.com/search?q=site:linkedin.com/in+"{}"&first={}'}

    def __init__(self, engine, company, timeout, conn_timeout, headers={}, proxies=[], jitter=1, safe=False, debug=False):
        self.links = []
        self.timeout = timeout
        self.proxies = proxies
        self.headers = headers
        self.conn_timeout = conn_timeout
        self.debug = debug
        self.safe = safe
        self.jitter = jitter

        self.engine = engine
        self.company = company
        self.key = 'linkedin.com/in'

        self.linkedin = {}
        self.users = {}
        self.user_count = 0
        self.output_count = 0

    def search(self):
        timer = self.start_timer()
        self.total_links = 0        # Total Links found by search engine
        self.page_links = 0         # Total links found by search engine w/ our domain in URL
        found_links = 0             # Local count to detect when no new links are found

        while timer.running:
            if self.total_links > 0 and found_links == self.page_links:
                timer.stop()
                return self.links

            found_links = self.page_links
            search_url = self.generateURL()
            resp = web_request(search_url, timeout=self.conn_timeout, headers=self.headers, proxies=self.proxies)

            if get_statuscode(resp) != 0:
                self.user_output(resp)
                self.pageParser(resp)
        timer.stop()
        return self.links

    def start_timer(self):
        timer = TaserTimeout(self.timeout)
        if self.timeout > 0:
            timer.start()
        return timer

    def generateURL(self):
        return self.URL[self.engine].format(self.company, self.page_links)

    def user_output(self, resp):
        if self.user_count > self.output_count:
            logger.info("{} : {}".format(self.user_count, resp.request.url))
            self.output_count = self.user_count

    def pageParser(self, resp):
        for link in extract_links(resp):
            try:
                url = str(link.get('href')).lower()
                self.total_links += 1
                if extract_webdomain(url) not in [self.engine, 'microsoft.com']:
                    self.page_links += 1
                    if self.key in url and self.extract_linkedin(link, self.company):
                        self.user_count += 1
            except:
                pass

    def extract_linkedin(self, link, company_name):
        '''
        Primary method responsible to parsing name from link string in
        search results. This is a hot mess @todo covert 2 regex!
        '''
        if self.safe and company_name.lower() not in link.text.lower():
            return False

        try:
            # Sanitize input
            x = unidecode(link.text.split("|")[0].split("...")[0])

            # Extract Name (if title provided)
            name = x.strip()
            for delim in ['-','|']:
                if delim in x:
                    name = link.text.split("–")[0].strip()

            try:
                # Quick split to extract title
                title = link.text.split("-")[1].strip()
                title = title.split("...")[0].split("|")[0].strip()
            except:
                title = "N/A"

            # Split name - first last
            tmp = name.split(' ')
            name = ''.join(e for e in tmp[0] if e.isalnum()) + " " + ''.join(e for e in tmp[1] if e.isalnum())

            # Exception catch 1st letter last name - Fname L.
            tmp = name.split(' ')
            if len(tmp[0]) <= 1 or len(tmp[-1]) <=1:
                raise Exception("\'{}\' Failed name parsing".format(link.text))
            elif tmp[0].endswith((".","|")) or tmp[-1].endswith((".","|")):
                raise Exception("\'{}\' Failed name parsing".format(link.text))

            k = name.lower()
            if k not in self.linkedin:
                self.linkedin[k] = {}
                self.linkedin[k]['last'] = name.split(' ')[1].lower()
                self.linkedin[k]['first'] = name.split(' ')[0].lower()
                self.linkedin[k]['title'] = title.strip().lower()
                self.linkedin[k]['format'] = formatter(args.nformat, self.linkedin[k]['first'], self.linkedin[k]['last'])
                logger.debug("PASS: {} (SAFE:{}) - {}".format(self.engine.upper(), self.safe, link.text), fg='green')
                return True

        except Exception as e:
            logger.debug("ERR: {} (SAFE:{}) - {}".format(self.engine.upper(), self.safe, str(e)), fg='yellow')

        logger.debug("FAIL: {} (SAFE:{}) - {}".format(self.engine.upper(), self.safe, link.text), fg='red')
        return False

def extract_links(resp):
    links = []
    soup = BeautifulSoup(resp.content, 'lxml')
    for link in soup.findAll('a'):
        links.append(link)
    return links

def formatter(nformat, first, last):
    name = nformat
    name = name.replace('{f}', first[0])
    name = name.replace('{first}', first)
    name = name.replace('{l}', last[0])
    name = name.replace('{last}', last)
    return name

def getUsers(engine, args):
    logger.info("Searching {} for valid employee names at \"{}\"".format(engine, args.company_name))
    c = CrossLinked(engine,  args.company_name, args.timeout, 3, args.header, args.proxy, args.jitter, args.safe,args.debug)
    if engine in c.URL.keys():
        c.search()
    if not c.linkedin:
        logger.warning('No results found')
    return c.linkedin

def main(args):
    names = {}
    for engine in args.engine:
        for name, data in getUsers(engine, args).items():
            try:
                id = formatter(args.nformat, data['first'], data['last'])
                if id not in names:
                    names[id] = data
            except:
                pass

    for id, data in names.items():
        if args.verbose:
            logger.success("{:30} - {}".format(data['first']+" "+data['last'], data['title']))
        ledger.info(id)
    logger.success("{} unique names added to {}!".format(len(names.keys()), args.outfile))

if __name__ == '__main__':
    banner()
    args = argparse.ArgumentParser(description="", formatter_class=argparse.RawTextHelpFormatter, usage=argparse.SUPPRESS)
    args.add_argument('--debug', dest="debug", action='store_true',help=argparse.SUPPRESS)
    args.add_argument('-t', dest='timeout', type=int, default=20,help='Max timeout per search (Default=20, 0=None)')
    args.add_argument('-j', dest='jitter', type=float, default=0,help='Jitter between requests (Default=0)')
    args.add_argument('-v', dest="verbose", action='store_true', help="Show names and titles recovered after enumeration")
    args.add_argument(dest='company_name', nargs='?', help='Target company name')

    s = args.add_argument_group("Search arguments")
    s.add_argument('-H', dest='header', type=str, default='', help='Add Header (\'name1=value1;name2=value2;\')')
    s.add_argument('--search', dest='engine', type=str, default='google,bing',help='Search Engine (Default=\'google,bing\')')
    s.add_argument("--safe", dest="safe", action='store_true',help="Only parse names with company in title (Reduces false positives)")

    o = args.add_argument_group("Output arguments")
    o.add_argument('-f', dest='nformat', type=str, required=True, help='Format names, ex: \'domain\{f}{last}\', \'{first}.{last}@domain.com\'')
    o.add_argument('-o', dest='outfile', type=str, default='names.txt', help='Change name of output file (default=names.txt')

    p = args.add_argument_group("Proxy arguments")
    pr = p.add_mutually_exclusive_group(required=False)
    pr.add_argument('--proxy', dest='proxy', action='append', default=[], help='Proxy requests (IP:Port)')
    pr.add_argument('--proxy-file', dest='proxy', default=False, type=lambda x: file_exists(args, x), help='Load proxies from file for rotation')
    args = args.parse_args()

    logger = setup_consoleLogger(logging.DEBUG if args.debug else logging.INFO)
    ledger = setup_fileLogger(args.outfile, mode='w')
    setattr(args, 'header', delimiter2dict(args.header))
    setattr(args, 'engine', delimiter2list(args.engine))

    try:
        main(args)
    except KeyboardInterrupt:
        logger.warning("Key event detected, closing...")
        exit(0)
