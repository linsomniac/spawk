#!/usr/bin/env python3
# vim: ts=4 sw=4 ai et

from unittest import mock, TestCase
import spawk
from io import StringIO
import sys

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
sample_sql = '''
-- Test SQL statements
CREATE TABLE foo (
   name TEXT,
   id INT NOT NULL
   );
-- And on a single line
CREATE TABLE bar ( length INT );
INSERT INTO foo VALUES ('Column', 1);
INSERT INTO bar VALUES (32);
'''


class TestMainWithSample(TestCase):
    def setUp(self):
        fileobj = StringIO(sample_data)
        self.t = spawk.Spawk(fileobj)

    def test_basic(self):
        self.assertEqual(''.join(self.t), sample_data)

    def test_grep_singlematch(self):
        self.t.grep('anim')
        self.assertEqual(
            ''.join(self.t), 'qui officia deserunt mollit anim id\n')

    def test_grep_multiline(self):
        self.t.grep('lit')
        self.assertEqual(
                ''.join(self.t),
                'adipiscing elit, sed do eiusmod tempor\nin reprehenderit in '
                'voluptate velit\nqui officia deserunt mollit anim id\n')

    def test_grep_multiexpr(self):
        self.t.grep('anim', 'occaecat')
        self.assertEqual(
                ''.join(self.t),
                'pariatur. Excepteur sint occaecat\n'
                'qui officia deserunt mollit anim id\n')

    def test_grep_linenumber(self):
        self.t.grep('anim')
        self.assertEqual(list(self.t)[0].line_number, 12)

    def test_fields(self):
        self.t.grep('anim').split()
        line = list(self.t)[0]
        self.assertEqual(line.fields[4], 'anim')
        self.assertEqual(len(line.fields), 6)

    def test_program(self):
        @self.t.begin()
        def begin(context):
            context.words = 0

        @self.t.every()
        def line(context, line):
            context.words += len(line.split())
        self.t.run()

        self.assertEqual(self.t.context.words, 69)

    def test_modified(self):
        @self.t.begin()
        def begin(context):
            context.words = 0

        @self.t.main()
        def make_hello(context, line):
            return 'hello'

        @self.t.main()
        def count(context, line):
            self.assertEqual(line, 'hello')
            context.words += len(line.split())
        self.t.run()

        self.assertEqual(self.t.context.words, 13)


class TestMainWithSampleAndContextData(TestCase):
    def setUp(self):
        fileobj = StringIO(sample_data)
        self.t = spawk.Spawk(fileobj)
        self.t.context.data = ''

    def test_pattern(self):
        @self.t.pattern(r'(anim|occaecat)')
        def line(context, line):
            context.data += line
        self.t.run()

        self.assertEqual(
                ''.join(self.t.context.data),
                'pariatur. Excepteur sint occaecat\n'
                'qui officia deserunt mollit anim id\n')

    def test_multi_pattern(self):
        @self.t.pattern(r'anim')
        @self.t.pattern(r'occaecat')
        def line(context, line):
            context.data += line
        self.t.run()

        self.assertEqual(
                ''.join(self.t.context.data),
                'pariatur. Excepteur sint occaecat\n'
                'qui officia deserunt mollit anim id\n')

    def test_multi_pattern_range(self):
        @self.t.pattern(r'anim')
        @self.t.range(r'aliqua', r'consequat')
        @self.t.pattern(r'occaecat')
        def line(context, line):
            context.data += line
        self.t.run()

        self.assertEqual(
                ''.join(self.t.context.data),
                'aliqua. Ut enim ad minim veniam,\n'
                'quis nostrud exercitation ullamco\n'
                'laboris nisi ut aliquip ex ea commodo\n'
                'consequat. Duis aute irure dolor\n'
                'pariatur. Excepteur sint occaecat\n'
                'qui officia deserunt mollit anim id\n')

    def test_range(self):
        @self.t.range(r'aliqua', r'consequat')
        def line(context, line):
            context.data += line
            if line.startswith('aliqua'):
                self.assertEqual(context.range.line_number, 1)
                self.assertFalse(context.range.is_last_line)
            if line.startswith('quis'):
                self.assertEqual(context.range.line_number, 2)
                self.assertFalse(context.range.is_last_line)
            if line.startswith('consequat'):
                self.assertEqual(context.range.line_number, 4)
                self.assertTrue(context.range.is_last_line)
        self.t.run()

        self.assertEqual(
                ''.join(self.t.context.data),
                'aliqua. Ut enim ad minim veniam,\n'
                'quis nostrud exercitation ullamco\n'
                'laboris nisi ut aliquip ex ea commodo\n'
                'consequat. Duis aute irure dolor\n')

    def test_range_single_line(self):
        @self.t.range(r'aliqua', r'veniam')
        def line(context, line):
            context.data += line
            self.assertEqual(context.range.line_number, 1)
            self.assertTrue(context.range.is_last_line)
        self.t.run()

        self.assertEqual(
                ''.join(self.t.context.data),
                'aliqua. Ut enim ad minim veniam,\n')

    def test_grep_and_pattern(self):
        self.t.grep(r'^a')

        @self.t.pattern(r'q')
        def line(context, line):
            context.data += line
        self.t.run()
        self.assertEqual(
                ''.join(self.t.context.data),
                'aliqua. Ut enim ad minim veniam,\n')

    def test_print_and_pattern(self):
        with mock.patch('sys.stdout.write') as mock_write:
            self.t.pattern(r'enim')()

            @self.t.pattern(r'cillum')
            def line(context, line):
                context.data += line
            self.t.run()

            mock_write.assert_has_calls([
                    mock.call('aliqua. Ut enim ad minim veniam,\n'),
                ])

            self.assertEqual(
                    ''.join(self.t.context.data),
                    'esse cillum dolore eu fugiat nulla\n')

    def test_eval(self):
        self.t.split()

        @self.t.eval('line.fields[0] == "aliqua."')
        def line(context, line):
            context.data += line
        self.t.run()

        self.assertEqual(
                ''.join(self.t.context.data),
                'aliqua. Ut enim ad minim veniam,\n')


class TestContinueWithSample(TestCase):
    def setUp(self):
        fileobj = StringIO(sample_data)
        self.t = spawk.Spawk(fileobj)

        @self.t.begin()
        def begin(context):
            context.words = 0

    def continue_main(self, t, decorator, *args):
        @decorator(*args)
        def line(context, line):
            context.words += len(line.split())
            return spawk.Continue

        @decorator(*args)
        def line2(context, line):
            context.words += len(line.split())
        t.run()

        self.assertEqual(t.context.words, 69)

    def test_continue_every(self):
        self.continue_main(self.t, self.t.every)

    def test_continue_pattern(self):
        self.continue_main(self.t, self.t.pattern, r'.*')

    def test_continue_eval(self):
        self.continue_main(self.t, self.t.eval, 'True')


class TestRangeSQL(TestCase):
    def setUp(self):
        fileobj = StringIO(sample_sql)
        self.t = spawk.Spawk(fileobj)
        self.t.context.data = ''

    def test_multiline_and_single_range(self):
        @self.t.range(r'CREATE TABLE', r'\);')
        def line(context, line):
            context.data += line
        self.t.run()

        self.assertEqual(
                ''.join(self.t.context.data),
                'CREATE TABLE foo (\n'
                '   name TEXT,\n'
                '   id INT NOT NULL\n'
                '   );\n'
                'CREATE TABLE bar ( length INT );\n')


class TestStdin(TestCase):
    def setUp(self):
        self.old_stdin = sys.stdin
        sys.stdin = StringIO(sample_data)
        self.t = spawk.Spawk()
        self.t.context.data = ''

    def tearDown(self):
        sys.stdin = self.old_stdin

    def test_multiline_and_single_range(self):
        @self.t.every()
        def line(context, line):
            context.data += line
        self.t.run()

        self.assertEqual(
                ''.join(self.t.context.data), sample_data)
