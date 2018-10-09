#!/usr/bin/env python3
# vim: ts=4 sw=4 ai et

import re
import sys


class FileFollower:
    '''Iterator that follows the changes to a file "tail -F"-like.
    This iterator will produce all the lines in a file and then monitor
    for changes to the file and produce new lines added to the end of the
    file.  If the file doesn't exist, it will wait for it's creation.
    If the file is truncated, removed and recreated, or a new filesystem
    is mounted on top of it, the file will be closed and reopened.

    Example:

        tc = TextChomp(FileFollower('syslog'))

    :param filename: Name of the file to follow.
    :param sleep_time: (float) Time to sleep between polls of the file.
    '''
    def __init__(self, filename, sleep_time=1):
        self.filename = filename
        self.sleep_time = sleep_time

    def _follow(self):
        '''INTERNAL: Generator that yields the lines within the file.
        It implements the logic of polling for file modifications and
        re-opening the file when appropriate.
        '''
        import time
        import os

        fp = None
        stats = None
        data = ''
        while True:
            if not fp:
                try:
                    fp = open(self.filename, 'r')
                    stats = os.stat(fp.fileno())
                except FileNotFoundError:
                    time.sleep(self.sleep_time)
                    continue

            next_block = fp.read(1024)
            if not next_block:
                try:
                    new_stats = os.stat(self.filename)
                except FileNotFoundError:
                    fp = None
                    continue
                if (
                        new_stats.st_ino != stats.st_ino
                        or new_stats.st_dev != stats.st_dev
                        or new_stats.st_size < stats.st_size):
                    fp = None
                else:
                    time.sleep(self.sleep_time)
                stats = new_stats
                continue

            data += next_block
            if '\n' not in next_block:
                continue

            for data in data.splitlines(True) + ['']:
                if data.endswith('\n'):
                    yield data

    def __iter__(self):
        return self._follow()


class String(str):
    '''A rich string object for TextChomp().
    This object is a string but with extra attributes specifying the
    line number within the input and the fields within the line from
    "string".split().
    '''
    def __new__(cls, s, line_number):
        return super().__new__(cls, s)

    def __init__(self, s, line_number):
        self.line_number = line_number


class StringIterator:
    '''INTERNAL: Wrapper that converts str()s to String()s.
    This is used on the inner-most layer of the TextChomp pipeline to
    convert the input lines into rich TextChomp.String() objects containing
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


class PatternIterator:
    '''INTERNAL: Pipeline Iterator wrapper implementing @pattern()
    Pipeline component that checks lines coming from the remainder
    of the pipeline and, if the pattern matches, calls a function for
    processing.

    :param program: The pipeline to consume lines from.
    :param context: Context() for passing to the function.  A "regex"
            attribute is set for the function call which has the regex
            match() object.
    :param body: The function to be run on pattern matches.
    :param pattern: A regular expression to match.
    '''
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


class CodeIterator:
    '''INTERNAL: Pipeline Iterator wrapper implementing @eval()
    Pipeline component that checks lines coming from the remainder
    of the pipeline and, if the code evaluates true, calls a function
    for processing.

    :param program: The pipeline to consume lines from.
    :param context: Context() for passing to the function.  A "regex"
            attribute is set for the function call which has the regex
            match() object.
    :param body: The function to be run on pattern matches.
    :param code: (str) Code to run that determines if function is run.
    '''
    def __init__(self, program, context, body, code):
        self.program = program
        self.context = context
        self.body = body
        self.code = code

    def __iter__(self):
        return self

    def __next__(self):
        line = next(self.program)
        self.context.line = line
        ret = eval(self.code, None, vars(self.context))
        del(self.context.line)
        if ret:
            self.context.eval = ret
            self.body(self.context, line)
            del(self.context.eval)
        return line


class RangeIterator:
    '''INTERNAL: Pipeline Iterator wrapper implementing @range()
    Pipeline component that checks lines coming from the remainder
    of the pipeline and, if the pattern matches, calls a function for
    processing.

    :param program: The pipeline to consume lines from.
    :param context: Context() for passing to the function.  For the
            life of the range, a "range" sub-context is set with
            "line_number" and "is_last_line" attributes.  The "regex"
            attribute has the start match object for every line except
            the one matching the end regex, where it is that match.
    :param body: The function to be run on all lines within the range.
    :param start: A regular expression matching the start of the range.
    :param end: A regular expression matching the end of the range.
    '''
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
        '''INTERNAL: Code implementing the range state machine.
        This detects the start of the range, calls the function until the
        end matches.
        '''
        if not self.in_range:
            m = self.start(line)
            if not m:
                return
            self.in_range = True
            self.context.range = Context()
            self.context.range.regex = m
            self.context.range.line_number = 0
            self.context.range.is_last_line = False

        self.context.range.line_number += 1
        m = self.end(line)
        if m:
            self.context.range.regex = m
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
    '''A simple object used as a context which attributes can be set on
    for use between the different functions in a TextChomp() processing
    pipeline.'''
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
        self.context = Context()

    def __iter__(self):
        return self.program_head

    def run(self):
        '''
        Run the processor defined.  This consumes the data in the input and
        runs any rules defined for processing that data.
        '''
        for f in self.begin_handlers:
            f(self.context)
        self.begin_handlers = []

        for line in self.program_head:
            pass

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
        def inner(f=_print):
            self.begin_handlers.append(f)
        return inner

    def pattern(self, pattern=''):
        '''
        Decorator for functions that are run when the pattern is matched.

        Example:

            @tc.pattern(r'hello\s+(\S+)')
            def hello(context, line):
                context.hello = line.regex.group(1)

            @tc.pattern()
            def every_line(context, line):
                context.linecount += 1

        :param pattern: Regular expression pattern which, when matched,
                triggers the decorated function.  If not specified, matches
                all lines.
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

            tc.context.lastline = ''

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


def _print(context, line):
    '''
    Default action which is used internally to print matches.  Used internally.
    This is the default if a decorator is called as a function rather than
    with "@pattern('match')", you use:

    t.pattern('match')()

    This is how Python accesses decorators with no associated function.
    '''
    sys.stdout.write(line)
