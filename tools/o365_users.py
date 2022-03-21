#!/usr/bin/env python3
# Author: m8r0wn
# License: GPLv3

########################################
# References:
# (And other awesome tools to checkout)
#######################################
# https://github.com/Raikia/UhOh365
# https://github.com/gremwell/o365enum

import argparse
import threading
from time import sleep
from taser.utils import file_exists, delimiter2dict
from taser.proto.http import web_request, get_statuscode
from taser.logx import setup_fileLogger, setup_consoleLogger

def o365_validateUser(user, timeout, headers={}, proxy=[], verbose=False):
    url = 'https://outlook.office365.com/autodiscover/autodiscover.json/v1.0/{user}?Protocol=Autodiscoverv1'
    headers['Accept'] = 'application/json'

    r = web_request(url.format(user=user), redirects=False, timeout=timeout, headers=headers, proxies=proxy)
    if get_statuscode(r) == 200:
            logger.success([user])
            ledger.info(user)
    elif verbose:
        logger.fail([user])

def gen_user(user, domain):
    return user+'@'+domain if args.domain else user

def main(args):
    logger.info(['Users', len(args.users)])
    logger.info(['Target', 'outlook.office365.com'])
    logger.info(['Method', 'Autodiscover\n'])
    logger.info('Starting O365 User Validation...')

    for user in args.users:
        o365_validateUser(gen_user(user,args.domain), args.timeout, args.headers, args.proxy, args.verbose)

        while threading.activeCount() >= args.max_threads:
            sleep(0.05)
    while threading.activeCount() > 1:
        sleep(0.05)

if __name__ == '__main__':
    VERSION = "v0.0.1"
    args = argparse.ArgumentParser(description="", formatter_class=argparse.RawTextHelpFormatter,usage=argparse.SUPPRESS)
    args.add_argument('-v', dest="verbose", action='store_true', help="Show results after each test")
    args.add_argument('-t', dest='timeout', type=int, default=20,help='Connection timeout')
    args.add_argument('-T', dest='max_threads', type=int, default=15, help='Max threads (Default=15)')
    args.add_argument('-o', dest='outfile', type=str, default='o365users.txt', help='Change name of output file (Default=o365users.txt)')
    args.add_argument('-H', dest='headers', type=str, default='', help='Add optional request headers (\'name1=value1;name2=value2\')')

    u = args.add_argument_group("Input arguments")
    u.add_argument('-d', dest='domain', type=str, default='',help='Domain name (Required if usernames provided)')
    u.add_argument('-u', dest='users', required=True, default=False, type=lambda x: file_exists(args, x), help='TXT File of usernames or emails to test')

    p = args.add_argument_group("Proxy arguments")
    pr = p.add_mutually_exclusive_group(required=False)
    pr.add_argument('--proxy', dest='proxy', action='append', default=[], help='Proxy requests (IP:Port)')
    pr.add_argument('--proxy-file', dest='proxy', default=False, type=lambda x: file_exists(args, x), help='Load proxies from file for rotation')
    args = args.parse_args()

    logger = setup_consoleLogger(spacers=[8])
    ledger = setup_fileLogger(args.outfile, mode='w')
    setattr(args, 'headers', delimiter2dict(args.headers))

    try:
        main(args)
    except KeyboardInterrupt:
        logger.warning("Key event detected, closing...")
        exit(0)
