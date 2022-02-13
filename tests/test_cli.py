#!/usr/bin/env python3
# vim: ts=4 sw=4 ai et

from unittest import mock, TestCase
from spawk.cli.main import cli
from click.testing import CliRunner


class TestCliMain(TestCase):
    def test_basic(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open('sample_input', 'w') as fp:
                fp.write('Hello world!')

            result = runner.invoke(cli, ['input', 'sample_input', 'upper'])
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(result.output, 'HELLO WORLD!')
