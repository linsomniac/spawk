#!/usr/bin/env python3
# vim: ts=4 sw=4 ai et

from .internal import (
    _print, StringIterator)
from .objects import Context
import re
import sys

if sys.hexversion >= 0x3060000:
    #  for python 3.6+
    import enum

    class ControlFlow(enum.Flag):
        '''Control flow: Flags for modifying engine control flow.

        Continue: Stop processing this record and continue with next.
        When returned from a pipeline member, this causes further parts of the
        pipeline not to be called on this record.

        Example:

            @t.pattern(r'COUNT_ME')
            def line(context, line):
                context.words += len(line.split())
                return spawk.Continue
        '''
        Continue = enum.auto()

    Continue = ControlFlow.Continue
else:
    #  for python <3.6
    class ControlFlow:
        pass

    class Continue(ControlFlow):
        pass


class Spawk:
    '''Engine for processing line-oriented text by specifying rules and code.
    It can be accessed either as an iterator of lines, or by specifying
    the processing and calling the run() method.

    Example:

        t = T
        t = spawk.Spawk(sys.stdin)
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

    ###########
    #  PIPELINE
    ###########
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

    ############
    #  DECORATOR
    ############
    def every(self):
        '''
        Decorator for functions that are called on every record.

        Example:

            @tc.every()
            def every_line(context, line):
                context.linecount += 1
        '''  # noqa: W605
        def inner(f):
            self.main_handlers.append(f)
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
            def wrapper(context, line):
                m = rx.search(line)
                if m:
                    self.context.regex = m
                    ret = f(context, line)
                    del(self.context.regex)
                    return ret
            self.main_handlers.append(wrapper)
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
            class RangeWrapper:
                def __init__(self, rx_start, rx_end, f):
                    self.rx_start = rx_start
                    self.rx_end = rx_end
                    self.f = f
                    self.in_range = False

                def __call__(self, context, line):
                    if not self.in_range:
                        m = self.rx_start(line)
                        if not m:
                            return
                        self.in_range = True
                        context.range = Context()
                        context.range.regex = m
                        context.range.line_number = 0
                        context.range.is_last_line = False

                    context.range.line_number += 1
                    m = self.rx_end(line)
                    if m:
                        context.range.regex = m
                        context.range.is_last_line = True
                    ret = self.f(context, line)
                    if not m:
                        return ret
                    self.in_range = False
                    del(context.range)
                    return ret

            self.main_handlers.append(RangeWrapper(rx_start, rx_end, f))
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
                spawk context as it's local context.  If it evaluates
                to true, the decorated function is run.
        '''
        def inner(f=_print):
            def wrapper(context, line):
                context.line = line
                eval_ret = eval(code, None, vars(context))
                del(context.line)
                if eval_ret:
                    context.eval = eval_ret
                    ret = f(context, line)
                    del(context.eval)
                    return ret
            self.main_handlers.append(wrapper)
            return f
        return inner
