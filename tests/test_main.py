#!/usr/bin/env python3

import gawk
from io import StringIO

sample_data = '''Lorem ipsum dolor sit amet, consectetur
adipiscing elit, sed do eiusmod tempor
incididunt ut labore et dolore magna
aliqua. Ut enim ad minim veniam,
quis nostrud exercitation ullamco
laboris nisi ut aliquip ex ea commodo
consequat. Duis aute irure dolor
in reprehenderit in voluptate velit
esse cillum dolore eu fugiat nulla
pariatur. Excepteur sint occaecat
cupidatat non proident, sunt in culpa
qui officia deserunt mollit anim id
est laborum.
'''


def test_basic():
    fileobj = StringIO(sample_data)
    t = gawk.Gawk(fileobj)
    assert ''.join(t) == sample_data


def test_grep_singlematch():
    fileobj = StringIO(sample_data)
    t = gawk.Gawk(fileobj).grep('anim')
    assert ''.join(t) == 'qui officia deserunt mollit anim id\n'


def test_grep_multiline():
    fileobj = StringIO(sample_data)
    t = gawk.Gawk(fileobj).grep('lit')
    assert ''.join(t) == (
        'adipiscing elit, sed do eiusmod tempor\nin reprehenderit in '
        'voluptate velit\nqui officia deserunt mollit anim id\n')


def test_grep_multiexpr():
    fileobj = StringIO(sample_data)
    t = gawk.Gawk(fileobj).grep('anim', 'occaecat')
    assert ''.join(t) == (
        'pariatur. Excepteur sint occaecat\n'
        'qui officia deserunt mollit anim id\n')


def test_grep_linenumber():
    fileobj = StringIO(sample_data)
    t = gawk.Gawk(fileobj).grep('anim')
    assert list(t)[0].line_number == 12


def test_fields():
    fileobj = StringIO(sample_data)
    t = gawk.Gawk(fileobj).grep('anim')
    line = list(t)[0]
    assert line.fields[4] == 'anim'
    assert len(line.fields) == 6


def test_program():
    fileobj = StringIO(sample_data)
    t = gawk.Gawk(fileobj)

    @t.begin()
    def begin(context):
        context.words = 0

    @t.pattern()
    def line(context, line):
        context.words += len(line.split())
    t.run()

    assert t.context.words == 69


def test_pattern():
    fileobj = StringIO(sample_data)
    t = gawk.Gawk(fileobj)
    t.context.data = ''

    @t.pattern(r'(anim|occaecat)')
    def line(context, line):
        context.data += line
    t.run()

    assert ''.join(t.context.data) == (
        'pariatur. Excepteur sint occaecat\n'
        'qui officia deserunt mollit anim id\n')


def test_range():
    fileobj = StringIO(sample_data)
    t = gawk.Gawk(fileobj)
    t.context.data = ''

    @t.range(r'aliqua', r'consequat')
    def line(context, line):
        context.data += line
        if line.startswith('aliqua'):
            assert context.range.line_number == 1
            assert context.range.is_last_line == False
        if line.startswith('quis'):
            assert context.range.line_number == 2
            assert context.range.is_last_line == False
        if line.startswith('consequat'):
            assert context.range.line_number == 4
            assert context.range.is_last_line == True
    t.run()

    assert ''.join(t.context.data) == (
        'aliqua. Ut enim ad minim veniam,\n'
        'quis nostrud exercitation ullamco\n'
        'laboris nisi ut aliquip ex ea commodo\n'
        'consequat. Duis aute irure dolor\n')


def test_range_single_line():
    fileobj = StringIO(sample_data)
    t = gawk.Gawk(fileobj)
    t.context.data = ''

    @t.range(r'aliqua', r'veniam')
    def line(context, line):
        context.data += line
        assert context.range.line_number == 1
        assert context.range.is_last_line == True
    t.run()

    assert ''.join(t.context.data) == 'aliqua. Ut enim ad minim veniam,\n'
