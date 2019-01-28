from . import AbstractRecords
import apache_log_parser


FORMAT_VHOST_COMBINED = (
        r'''%v:%p %h %l %u %t \"%r\" %>s '''
        '''%O \"%{Referer}i\" \"%{User-Agent}i\"''')
FORMAT_COMBINED = (
        r'''%h %l %u %t "%r" %>s %O "%{Referer}i" "%{User-Agent}i"''')
FORMAT_COMMON = r'''%h %l %u %t \"%r\" %>s %O'''


class ApacheLogRecords(AbstractRecords):
    def __init__(self, in_fileobj, fmt=FORMAT_VHOST_COMBINED):
        self.in_fileobj = in_fileobj
        self.parser = apache_log_parser.make_parser(fmt)

    def __iter__(self):
        return self

    def __next__(self):
        line = self.in_fileobj.readline()
        if not line:
            raise StopIteration
        return self.parser(line)
