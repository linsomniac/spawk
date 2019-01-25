#!/usr/bin/env python3
# vim: ts=4 sw=4 ai et

from unittest import mock, TestCase
import spawk


class ReturnList:
    def __init__(self, return_values):
        self.return_values = return_values

    def __call__(self, *args):
        value = self.return_values.pop(0)
        if (isinstance(value, Exception)
                or isinstance(value, KeyboardInterrupt)):
            raise value
        return value


class FakeFile:
    def __init__(self, data):
        self.data = data

    def read(self, *args):
        if not self.data:
            return ''
        return self.data.pop(0)

    def fileno(self):
        return 3


class FakeStat:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


read_data = ReturnList([
    FileNotFoundError(),
    FakeFile([
        'first ',
        'line\n',
        'second line\n',
        'third line\n',
        ]),
    FakeFile([
        'fourth line\n',
        'fifth line\n',
        ]),
    FakeFile([
        'sixth line\n',
        ]),
    FakeFile([
        'seventh line\n',
        ]),
    KeyboardInterrupt(),
    ])
stat_data = ReturnList([
    FakeStat(st_dev=1, st_ino=1, st_size=2),    # open
    FakeStat(st_dev=1, st_ino=1, st_size=2),    # 0-size read
    FileNotFoundError(),                        # new file, 0-size read
    FakeStat(st_dev=1, st_ino=1, st_size=2),    # open
    FakeStat(st_dev=1, st_ino=1, st_size=1),    # new file, size decrease
    FakeStat(st_dev=1, st_ino=1, st_size=2),    # open
    FakeStat(st_dev=1, st_ino=2, st_size=2),    # new file
    FakeStat(st_dev=1, st_ino=2, st_size=2),    # open
    FakeStat(st_dev=2, st_ino=2, st_size=2),    # new file
    ])


class TestFollower(TestCase):
    def test_follower(self):
        opener = mock.Mock(side_effect=read_data)
        stater = mock.Mock(side_effect=stat_data)

        lines = []
        with mock.patch('spawk.input.open', opener) as m_open:  # noqa: W0612
            with mock.patch('os.stat', stater) as m_stat:     # noqa: W0612
                f = spawk.FileFollower('foo', sleep_time=0.001)
                for line in f:
                    lines.append(line)

        self.assertEqual(
                read_data.return_values, [], 'read_data not fully consumed')
        self.assertEqual(
                stat_data.return_values, [], 'stat_data not fully consumed')
        self.assertEqual(lines[0], 'first line\n')
        self.assertEqual(len(lines), 7)
