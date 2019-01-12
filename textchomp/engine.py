#!/usr/bin/env python3
# vim: ts=4 sw=4 ai et

import re
from .internal import (
    _print, StringIterator, EveryIterator, RangeIterator, CodeIterator,
    PatternIterator,)
from .objects import Context


class ControlFlow:
    '''Base class for control-flow return objects'''
    pass


class Continue(ControlFlow):
    '''Control flow: Stop processing this record and continue with next.
    When returned from a pipeline member, this causes further parts of the
    pipeline not to be called on this record.'''
    pass


class TextChomp:
    '''Engine for processing line-oriented text by specifying rules and code.
    It can be accessed either as an iterator of lines, or by specifying
    the processing and calling the run() method.

    Example:

        t = T
        t = textchomp.TextChomp(sys.stdin)
        t.context.data = ''

        @t.range(r'CREATE TABLE', r'\);')
        def line(context, line):
            context.data += (('line %d:' % context.range.line_number) + line)
            if context.range.is_last_line:
                print(context.data)
                context.data = ''
    '''  # noqa: W605
    def __init__(self, fileobj):
        self.program_head = StringIterator(fileobj)
        self.begin_handlers = []
        self.main_handlers = []
        self.context = Context()

    def __iter__(self):
        return self.program_head

    def run(self):
        '''
        Run the processor.  This consumes the data in the input and
        runs any rules defined for processing that data.
        '''
        for f in self.begin_handlers:
            f(self.context)
        self.begin_handlers = []

        for line in self.program_head:
            if line is Continue:
                continue
            for handler in self.main_handlers:
                ret = handler(self.context, line)
                if ret is Continue:
                    break
                if ret is not None:
                    line = ret

    def grep(self, *args):
        '''
        Adds a pattern matcher filter to the processor.

        :param *args: Regular expression to match, if multiple arguments are
                given then the matches are combined as in an "or" (if any
                match).
        :rtype: Returns a reference to self, can be used to build up a
                pipeline of processors.
        '''
        def inner(data, *args):
            rxlist = [re.compile(x).search for x in args]
            for line in data:
                for rx in rxlist:
                    match = rx(line)
                    if match:
                        yield line

        self.program_head = inner(self.program_head, *args)
        return self

    def split(self, sep=None, maxsplit=-1):
        '''
        Add a "fields" attribute to the line objects, as str.split().
        The input lines are split into a list, and stored in the "fields"
        attribute of the String().

        :param sep: String to split on, as with str.split() (Default: None)
        :param maxsplit: Maximum number of splits to do as with str.split()
                (Default: -1)
        :rtype: Returns a reference to self, can be used to build up a
                pipeline of processors.
        '''
        def inner(data, sep, maxsplit):
            for line in data:
                line.fields = line.split(sep, maxsplit)
                yield line

        self.program_head = inner(self.program_head, sep, maxsplit)
        return self

    def begin(self):
        '''
        Decorator for functions which are run at the beginning of the
        text processing session.

        Example:

            @tc.begin()
            def initialize(context):
                context.wordcount = 0
        '''
        def inner(f):
            self.begin_handlers.append(f)
        return inner

    def main(self):
        '''
        Decorator for functions which are run at the beginning of the
        text processing session.

        Example:

            @tc.main()
            def count_words(context, line):
                context.wordcount += len(line.split)
        '''
        def inner(f):
            self.main_handlers.append(f)
        return inner

    def every(self):
        '''
        Decorator for functions that are called on every record.

        Example:

            @tc.every()
            def every_line(context, line):
                context.linecount += 1
        '''  # noqa: W605
        def inner(f=_print):
            self.program_head = EveryIterator(
                    self.program_head, self.context, f)
            return f
        return inner

    def pattern(self, pattern):
        '''
        Decorator for functions that are run when the pattern is matched.

        Example:

            @tc.pattern(r'hello\s+(\S+)')
            def hello(context, line):
                context.hello = line.regex.group(1)

        :param pattern: Regular expression pattern which, when matched,
                triggers the decorated function.
        '''  # noqa: W605
        rx = re.compile(pattern)

        def inner(f=_print):
            self.program_head = PatternIterator(
                    self.program_head, self.context, f, rx.search)
            return f
        return inner

    def range(self, start, end):
        '''
        Deocator that defines a starting and ending pattern and runs the
        decorated function for every line between (and including) the
        patterns.

        The context object includes a "range" attribute, itself a Context()
        which exists for the life of the range processing and includes
        attributes "line_number" and "is_last_line" for identifying where
        in the range processing is occurring and for triggering processing
        when the end of range pattern matches.

        Example:

            #  Extract CREATE TABLE statements and add line numbers
            @tc.range(r'CREATE TABLE', r'\);')
            def line(context, line):
                context.data += ((
                    'line %d:' % context.range.line_number) + line)
                if context.range.is_last_line:
                    print(context.data)
                    context.data = ''

        :param start: Regular expression pattern which identifies the
                starting line for the decorated function to operate on.
        :param end: Regular expression pattern which identifies the
                last line of the range.
        '''  # noqa: W605
        rx_start = re.compile(start).search
        rx_end = re.compile(end).search

        def inner(f=_print):
            self.program_head = RangeIterator(
                    self.program_head, self.context, f, rx_start, rx_end)
            return f
        return inner

    def eval(self, code):
        '''
        Decorator for functions that are run when a bit of Python code
        evaluates to True.

        Example:

            tc.context.lastline = None

            @tc.eval('lastline != line')
            def unique(ctx, line):
                sys.stdout.write(line)
                ctx.lastline = line

        :param code: String of Python code that is evaluated, with the
                textchomp context as it's local context.  If it evaluates
                to true, the decorated function is run.
        '''
        def inner(f=_print):
            self.program_head = CodeIterator(
                    self.program_head, self.context, f, code)
            return f
        return inner
