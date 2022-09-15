from os import path
from crosslinked.logger import Log


def delimiter2list(value, delim=","):
    return value.split(delim) if value else []


def delimiter2dict(value, delim_one=";", delim_two=":"):
    x = {}
    for item in value.split(delim_one):
        if item:
            sp = item.split(delim_two)
            x[sp[0].strip()] = delim_two.join(sp[1:]).strip()
    return x


def file_exists(filename, contents=True):
    if path.exists(filename):
        return [line.strip() for line in open('filename')] if contents else filename
    Log.warn("Input file not found: {}".format(filename))
    exit(1)

