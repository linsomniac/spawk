from ..internal import StringIterator
from . import AbstractRecords


class LineRecords(AbstractRecords):
    def __init__(self, in_fileobj):
        self.in_fileobj = in_fileobj

    def __iter__(self):
        return StringIterator(self.in_fileobj)
