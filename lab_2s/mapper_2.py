#!/usr/bin/env python
__author__ = 'Pavel Gladkov'


import sys


if __name__ == '__main__':

    for line in sys.stdin:
        line = line.strip()
        try:
            url, val = line.split('\t')
        except ValueError:
            continue

        print("%s\t%s" % (val, url))