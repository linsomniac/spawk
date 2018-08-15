#!/usr/bin/env python3

import re


class String(str):
    def __new__(cls, s, line_number):
        return super().__new__(cls, s)

    def __init__(self, s, line_number):
        self.line_number = line_number


class StringIterator:
    def __init__(self, data):
        self.data = data
        self.lineno = 0

    def __iter__(self):
        return self

    def __next__(self):
        self.lineno += 1
        return String(self.data.__next__(), self.lineno)


class PatternIterator:
    def __init__(self, program, context, body, pattern):
        self.program = program
        self.context = context
        self.body = body
        self.pattern = pattern

    def __iter__(self):
        return self

    def __next__(self):
        line = next(self.program)
        self.body(self.context, line)
        return line


class Context:
    pass


class Gawk:
    def __init__(self, fileobj):
        self.program_head = StringIterator(fileobj)
        self.begin_handlers = []
        self.context = Context()

    def __iter__(self):
        return self.program_head

    def run(self):
        for f in self.begin_handlers:
            f(self.context)
        self.begin_handlers = []

        for line in self.program_head:
            pass

    def _grep(self, data, *args):
        rxlist = [re.compile(x).search for x in args]
        for line in data:
            for rx in rxlist:
                match = rx(line)
                if match:
                    yield line

    def grep(self, *args):
        self.program_head = self._grep(self.program_head, *args)
        return self

    def begin(self):
        def inner_begin(f):
            self.begin_handlers.append(f)
        return inner_begin

    def pattern(self, pattern=''):
        rx = re.compile(pattern)

        def inner_begin(f):
            self.program_head = PatternIterator(
                    self.program_head, self.context, f, rx.match)
        return inner_begin
