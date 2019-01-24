#!/usr/bin/env python3
# vim: ts=4 sw=4 ai et

from .objects import String

import sys


class StringIterator:
    '''INTERNAL: Wrapper that converts str()s to String()s.
    This is used on the inner-most layer of the Spawk pipeline to
    convert the input lines into rich Spawk.String() objects containing
    the line number.

    :param data: Iterator that this class wraps.
    '''
    def __init__(self, data):
        self.data = data
        self.lineno = 0

    def __iter__(self):
        return self

    def __next__(self):
        self.lineno += 1
        return String(self.data.__next__(), self.lineno)


def _print(context, line):
    '''INTERNAL: Default action which is used internally to print matches.
    This is the default if a decorator is called as a function rather than
    with "@pattern('match')", you use:

    t.pattern('match')()

    This is how Python accesses decorators with no associated function.
    '''
    sys.stdout.write(line)
