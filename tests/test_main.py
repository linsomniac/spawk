#!/usr/bin/env python3
# vim: ts=4 sw=4 ai et

from .context import spawk
from io import StringIO
from unittest import mock

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
    t = spawk.Spawk(fileobj)
    assert ''.join(t) == sample_data


def test_grep_singlematch():
    fileobj = StringIO(sample_data)
    t = spawk.Spawk(fileobj).grep('anim')
    assert ''.join(t) == 'qui officia deserunt mollit anim id\n'


def test_grep_multiline():
    fileobj = StringIO(sample_data)
    t = spawk.Spawk(fileobj).grep('lit')
    assert ''.join(t) == (
        'adipiscing elit, sed do eiusmod tempor\nin reprehenderit in '
        'voluptate velit\nqui officia deserunt mollit anim id\n')


def test_grep_multiexpr():
    fileobj = StringIO(sample_data)
    t = spawk.Spawk(fileobj).grep('anim', 'occaecat')
    assert ''.join(t) == (
        'pariatur. Excepteur sint occaecat\n'
        'qui officia deserunt mollit anim id\n')


def test_grep_linenumber():
    fileobj = StringIO(sample_data)
    t = spawk.Spawk(fileobj).grep('anim')
    assert list(t)[0].line_number == 12


def test_fields():
    fileobj = StringIO(sample_data)
    t = spawk.Spawk(fileobj).grep('anim').split()
    line = list(t)[0]
    assert line.fields[4] == 'anim'
    assert len(line.fields) == 6


def test_program():
    fileobj = StringIO(sample_data)
    t = spawk.Spawk(fileobj)

    @t.begin()
    def begin(context):
        context.words = 0

    @t.every()
    def line(context, line):
        context.words += len(line.split())
    t.run()

    assert t.context.words == 69


def test_pattern():
    fileobj = StringIO(sample_data)
    t = spawk.Spawk(fileobj)
    t.context.data = ''

    @t.pattern(r'(anim|occaecat)')
    def line(context, line):
        context.data += line
    t.run()

    assert ''.join(t.context.data) == (
        'pariatur. Excepteur sint occaecat\n'
        'qui officia deserunt mollit anim id\n')


def test_multi_pattern():
    fileobj = StringIO(sample_data)
    t = spawk.Spawk(fileobj)
    t.context.data = ''

    @t.pattern(r'anim')
    @t.pattern(r'occaecat')
    def line(context, line):
        context.data += line
    t.run()

    assert ''.join(t.context.data) == (
        'pariatur. Excepteur sint occaecat\n'
        'qui officia deserunt mollit anim id\n')


def test_multi_pattern_range():
    fileobj = StringIO(sample_data)
    t = spawk.Spawk(fileobj)
    t.context.data = ''

    @t.pattern(r'anim')
    @t.range(r'aliqua', r'consequat')
    @t.pattern(r'occaecat')
    def line(context, line):
        context.data += line
    t.run()

    assert ''.join(t.context.data) == (
        'aliqua. Ut enim ad minim veniam,\n'
        'quis nostrud exercitation ullamco\n'
        'laboris nisi ut aliquip ex ea commodo\n'
        'consequat. Duis aute irure dolor\n'
        'pariatur. Excepteur sint occaecat\n'
        'qui officia deserunt mollit anim id\n')


def test_range():
    fileobj = StringIO(sample_data)
    t = spawk.Spawk(fileobj)
    t.context.data = ''

    @t.range(r'aliqua', r'consequat')
    def line(context, line):
        context.data += line
        if line.startswith('aliqua'):
            assert context.range.line_number == 1
            assert context.range.is_last_line is False
        if line.startswith('quis'):
            assert context.range.line_number == 2
            assert context.range.is_last_line is False
        if line.startswith('consequat'):
            assert context.range.line_number == 4
            assert context.range.is_last_line is True
    t.run()

    assert ''.join(t.context.data) == (
        'aliqua. Ut enim ad minim veniam,\n'
        'quis nostrud exercitation ullamco\n'
        'laboris nisi ut aliquip ex ea commodo\n'
        'consequat. Duis aute irure dolor\n')


def test_range_single_line():
    fileobj = StringIO(sample_data)
    t = spawk.Spawk(fileobj)
    t.context.data = ''

    @t.range(r'aliqua', r'veniam')
    def line(context, line):
        context.data += line
        assert context.range.line_number == 1
        assert context.range.is_last_line is True
    t.run()

    assert ''.join(t.context.data) == 'aliqua. Ut enim ad minim veniam,\n'


def test_grep_and_pattern():
    fileobj = StringIO(sample_data)
    t = spawk.Spawk(fileobj)
    t.grep(r'^a')
    t.context.data = ''

    @t.pattern(r'q')
    def line(context, line):
        context.data += line
    t.run()
    assert ''.join(t.context.data) == 'aliqua. Ut enim ad minim veniam,\n'


def test_print_and_pattern():
    fileobj = StringIO(sample_data)
    t = spawk.Spawk(fileobj)

    with mock.patch('sys.stdout.write') as mock_write:

        t.pattern(r'enim')()

        t.context.data = ''

        @t.pattern(r'cillum')
        def line(context, line):
            context.data += line

        t.run()

        mock_write.assert_has_calls([
                mock.call('aliqua. Ut enim ad minim veniam,\n'),
            ])

        assert ''.join(
            t.context.data) == 'esse cillum dolore eu fugiat nulla\n'


def test_eval():
    fileobj = StringIO(sample_data)
    t = spawk.Spawk(fileobj).split()

    t.context.data = ''

    @t.eval('line.fields[0] == "aliqua."')
    def line(context, line):
        context.data += line

    t.run()

    assert ''.join(t.context.data) == 'aliqua. Ut enim ad minim veniam,\n'


def continue_main(t, decorator, *args):
    @t.begin()
    def begin(context):
        context.words = 0

    @decorator(*args)
    def line(context, line):
        context.words += len(line.split())
        return spawk.Continue

    @decorator(*args)
    def line2(context, line):
        context.words += len(line.split())
    t.run()

    assert t.context.words == 69


def test_continue_every():
    fileobj = StringIO(sample_data)
    t = spawk.Spawk(fileobj)
    continue_main(t, t.every)


def test_continue_pattern():
    fileobj = StringIO(sample_data)
    t = spawk.Spawk(fileobj)
    continue_main(t, t.pattern, r'.*')


def test_continue_eval():
    fileobj = StringIO(sample_data)
    t = spawk.Spawk(fileobj)
    continue_main(t, t.eval, 'True')


def test_modified():
    fileobj = StringIO(sample_data)
    t = spawk.Spawk(fileobj)

    @t.begin()
    def begin(context):
        context.words = 0

    @t.main()
    def make_hello(context, line):
        return 'hello'

    @t.main()
    def count(context, line):
        assert line == 'hello'
        context.words += len(line.split())
    t.run()

    assert t.context.words == 13
