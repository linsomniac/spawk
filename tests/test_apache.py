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

    def test_eval(self):
        self.t.context.bytes_tx = 0

        @self.t.eval('line["status"] == "200"')
        def logent(context, record):
            context.bytes_tx += int(record['bytes_tx'])
        self.t.run()

        self.assertEqual(self.t.context.bytes_tx, 35223)

#dict_keys(['remote_host', 'remote_logname', 'remote_user', 'time_received', 'time_received_datetimeobj', 'time_received_isoformat', 'time_received_tz_datetimeobj', 'time_received_tz_isoformat', 'time_received_utc_datetimeobj', 'time_received_utc_isoformat', 'request_first_line', 'request_method', 'request_url', 'request_http_ver', 'request_url_scheme', 'request_url_netloc', 'request_url_path', 'request_url_query', 'request_url_fragment', 'request_url_username', 'request_url_password', 'request_url_hostname', 'request_url_port', 'request_url_query_dict', 'request_url_query_list', 'request_url_query_simple_dict', 'status', 'bytes_tx', 'request_header_referer', 'request_header_user_agent', 'request_header_user_agent__browser__family', 'request_header_user_agent__browser__version_string', 'request_header_user_agent__os__family', 'request_header_user_agent__os__version_string', 'request_header_user_agent__is_mobile'])
