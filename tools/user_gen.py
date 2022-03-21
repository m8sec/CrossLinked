#!/usr/bin/env python3
# Author: m8r0wn
# License: GPLv3

import argparse
from os import path

def name_formatter(nformat, first, last):
    name = nformat
    name = name.replace('{f}', first[0])
    name = name.replace('{first}', first)
    name = name.replace('{l}', last[0])
    name = name.replace('{last}', last)
    return name

def main(args):
    tmp = []

    for lname in args.last:
        for fname in args.first:
            user = name_formatter(args.nformat, fname, lname)
            if user not in tmp:
                tmp.append(user)

    openFile = open(args.outfile, 'a')
    for account in tmp:
        openFile.write("{}\n".format(account))
    openFile.close()

    print("\n[+] Username list created: {}\n".format(args.outfile))

def file_exists(parser, filename):
    # Used with argparse to check if input files exists
    if not path.exists(filename):
        parser.error("Input file not found: {}".format(filename))
    return [x.strip() for x in open(filename)]

if __name__ == '__main__':
    VERSION = "0.0.1"
    args = argparse.ArgumentParser(description="", formatter_class=argparse.RawTextHelpFormatter, usage=argparse.SUPPRESS)
    args.add_argument('-first', dest='first', default=False, type=lambda x: file_exists(args, x), help='txt file of first names')
    args.add_argument('-last', dest='last', default=False, type=lambda x: file_exists(args, x),help='txt file of last names')
    args.add_argument('-f','-format', dest='nformat', type=str, required=True, help='Format names, ex: \'domain\{f}{last}\', \'{first}.{last}@domain.com\'')
    args.add_argument('-o', dest='outfile', type=str, default='users.txt', help='Change name of output file (default: users.txt')
    args = args.parse_args()
    main(args)
