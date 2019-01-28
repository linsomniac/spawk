#!/usr/bin/env python3
# vim: ts=4 sw=4 ai et

from unittest import TestCase
import spawk
from spawk.parser.apache_log import ApacheLogRecords, FORMAT_COMBINED
from io import StringIO

sample_data = (
'''10.1.1.2 - - [27/Jan/2019:17:40:34 -0700] "GET / HTTP/1.0" 200 467 "-" "check_http/v2.1.2 (monitoring-plugins 2.1.2)"
127.0.0.1 - - [27/Jan/2019:17:40:39 -0700] "GET /server-status?auto HTTP/1.1" 200 776 "-" "Go-http-client/1.1"
10.1.1.1 - - [27/Jan/2019:17:40:49 -0700] "GET /osm/slippymap.html HTTP/1.1" 200 1818 "-" "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:64.0) Gecko/20100101 Firefox/64.0"
10.1.1.1 - - [27/Jan/2019:17:40:49 -0700] "GET /osm/style.css HTTP/1.1" 404 735 "http://osm1.stg.realgo.com/osm/slippymap.html" "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:64.0) Gecko/20100101 Firefox/64.0"
10.1.1.1 - - [27/Jan/2019:17:40:50 -0700] "GET /favicon.ico HTTP/1.1" 404 733 "-" "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:64.0) Gecko/20100101 Firefox/64.0"
10.1.1.1 - - [27/Jan/2019:17:40:50 -0700] "GET /osm/8/53/97.png HTTP/1.1" 200 22704 "http://osm1.stg.realgo.com/osm/slippymap.html" "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:64.0) Gecko/20100101 Firefox/64.0"
10.1.1.1 - - [27/Jan/2019:17:40:50 -0700] "GET /osm/8/54/99.png HTTP/1.1" 200 9458 "http://osm1.stg.realgo.com/osm/slippymap.html" "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:64.0) Gecko/20100101 Firefox/64.0"''')


class TestApacheLog(TestCase):
    def setUp(self):
        fileobj = StringIO(sample_data)
        self.t = spawk.Spawk(ApacheLogRecords(fileobj, FORMAT_COMBINED))
        self.t.context.data = ''

    def test_basic(self):
        @self.t.every()
        def logent(context, record):
            context.data += record['status']
        self.t.run()

        self.assertEqual(
                ''.join(self.t.context.data),
                '200200200404404200200')
