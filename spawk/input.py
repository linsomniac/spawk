#!/usr/bin/env python3
# vim: ts=4 sw=4 ai et


class FileFollower:
    '''Iterator that follows the changes to a file "tail -F"-like.
    This iterator will produce all the lines in a file and then monitor
    for changes to the file and produce new lines added to the end of the
    file.  If the file doesn't exist, it will wait for it's creation.
    If the file is truncated, removed and recreated, or a new filesystem
    is mounted on top of it, the file will be closed and reopened.

    Example:

        tc = Spawk(FileFollower('syslog'))

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
