#!/usr/bin/env python3

import re


class String(str):
    def __new__(cls, s, line_number):
        return super().__new__(cls, s)

    def __init__(self, s, line_number):
        self.line_number = line_number
        self.fields = s.split()


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
        m = self.pattern(line)
        if m:
            self.context.regex = m
            self.body(self.context, line)
            del(self.context.regex)
        return line


class RangeIterator:
    def __init__(self, program, context, body, start, end):
        self.program = program
        self.context = context
        self.body = body
        self.start = start
        self.end = end
        self.in_range = False

    def __iter__(self):
        return self

    def _engine(self, line):
        if not self.in_range:
            m = self.start(line)
            if not m:
                return
            self.in_range = True
            self.context.range = Context()
            self.context.range.line_number = 0
            self.context.range.is_last_line = False

        self.context.range.line_number += 1
        m = self.end(line)
        if m:
            self.context.range.is_last_line = True
        self.body(self.context, line)
        if not m:
            return
        self.in_range = False
        del(self.context.range)

    def __next__(self):
        line = next(self.program)
        self._engine(line)
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
                    self.program_head, self.context, f, rx.search)
        return inner_begin

    def range(self, start, end):
        rx_start = re.compile(start).search
        rx_end = re.compile(end).search

        def inner_begin(f):
            self.program_head = RangeIterator(
                    self.program_head, self.context, f, rx_start, rx_end)
        return inner_begin
