'''
Spawk parsers that will produce records for processing by the Spawk engine.
'''


class AbstractRecords:
    def __next__(self):
        raise NotImplementedError()
