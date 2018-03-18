#!/usr/bin/env python3
#
# Copyright (c) 2018-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
#

import asyncio
import argparse
import colour_runner.runner
import dns.message
import inspect
import sys
import unittest

from dohproxy import client_protocol, constants, utils
from functools import wraps
from pygments import highlight
from unittest.mock import patch


def async_test(f):
    def wrapper(*args, **kwargs):
        if inspect.iscoroutinefunction(f):
            future = f(*args, **kwargs)
        else:
            coroutine = asyncio.coroutine(f)
            future = coroutine(*args, **kwargs)
        asyncio.get_event_loop().run_until_complete(future)
    return wrapper


def save_to_store(f):
    @wraps(f)
    def call(*args, **kw):
        args[0]._result_store[f.__name__] = (args[1:], kw,)
        return f(*args, **kw)
    return call


def extract_from_headers(headers, key):
    for k, v in headers:
        if k == key:
            return v


def modify_headers(headers, key, value):
    new_headers = []
    for k, v in headers:
        if k == key:
            new_headers.append((key, value))
        else:
            new_headers.append((k, v))
    return new_headers


class DOHTextTestResult(colour_runner.runner.ColourTextTestResult):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.colours['fail'] = self._terminal.bold_yellow

    def formatErr(self, err):
        return '{}\n{}'.format(err[1].__class__.__name__, err[1].args[0])

    def addSuccess(self, test):
        unittest.result.TestResult.addSuccess(self, test)
        self.printResult('.', 'OK', 'success')

    def addError(self, test, err):
        self.failures.error((test, self.formatErr(err)))
        self.printResult('F', 'ERROR', 'error')

    def addFailure(self, test, err):
        self.failures.append((test, self.formatErr(err)))
        self.printResult('F', 'WARNING', 'fail')

    def printErrorList(self, flavour, errors):
        colour = self.colours[flavour.lower()]
        for test, err in errors:
            self.stream.writeln(self.separator1)
            title = '%s: %s' % (flavour, self.getLongDescription(test))
            self.stream.writeln(colour(title))
            print(type(err))
            self.stream.writeln(self.separator2)
            self.stream.writeln(highlight(err, self.lexer, self.formatter))


class DOHTestRunner(unittest.runner.TextTestRunner):
    """ A test runner that uses color in its output and customize signal """
    resultclass = DOHTextTestResult


class Client(client_protocol.StubServerProtocol):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._result_store = {}

    @save_to_store
    def on_answer(self, addr, msg):
        pass

    @save_to_store
    def on_message_received(self, stream_id, msg):
        return super().on_message_received(stream_id, msg)

    @save_to_store
    def on_recv_response(self, stream_id, headers):
        return super().on_recv_response(stream_id, headers)

    def from_store(self, name):
        return self._result_store[name]

    def _on_post_bad_body(self, client, stream_id, body):
        return super().on_send_data(client, stream_id, b"badcontent")

    def _on_start_request_bad_body(self, client, headers, end_stream):
        headers = modify_headers(
            headers,
            'content-length',
            str(len(b"badcontent"))
        )
        return super().on_start_request(client, headers, end_stream)

    def _on_start_request_bad_method(self, client, headers, end_stream):
        headers = modify_headers(headers, ':method', 'FOO')
        return super().on_start_request(client, headers, end_stream)

    def _on_start_request_head_method(self, client, headers, end_stream):
        headers = modify_headers(headers, ':method', 'HEAD')
        return super().on_start_request(client, headers, end_stream)

    def _on_start_request_bad_dns(self, client, headers, end_stream):
        headers = modify_headers(
            headers,
            ':path',
            self._make_get_path(b"badcontent")
        )
        return super().on_start_request(client, headers, end_stream)


class ServerIntegrationBaseClassTest(object):
    ARGS = None

    def setUp(self):
        self.logger = utils.configure_logger(
            'doh-integration', level=self.ARGS.level
        )
        self.logger.propagate = self.ARGS.propagate_logs
        self.client = Client(args=self.ARGS, logger=self.logger)

    @async_test
    async def test_identical_id_on_reply(self):
        """
        The response from a DNS query should contain the same ID than what was
        sent.
        """
        q = dns.message.make_query(qname='www.example.com', rdtype='A')
        orig_qid = q.id
        await self.client.make_request(
            None,
            q
        )
        addr, msg = self.client.from_store('on_answer')[0]
        r = dns.message.from_wire(msg)
        self.assertEqual(
            orig_qid, r.id, "Query and Response IDs are not matching."
        )

    @async_test
    async def test_id_is_zero(self):
        """
        The response from a DNS query should contain the same ID than what was
        sent and should support ID=0.
        """
        q = dns.message.make_query(qname='www.example.com', rdtype='A')
        await self.client.make_request(
            None,
            q
        )
        msg = self.client.from_store('on_message_received')[0][1]
        r = dns.message.from_wire(msg)
        if r.id != 0:
            self.fail("Response ID was not set to 0: %d" % r.id)

    @async_test
    async def test_not_implemented_method(self):
        """
        Test that when a method which is not implemented is sent to the server,
        we get a 501 back.
        """
        with patch(
                '__main__.Client.on_start_request',
                new=Client._on_start_request_bad_method):
            q = dns.message.make_query(qname='www.example.com', rdtype='A')
            with self.assertRaises(Exception):
                await self.client.make_request(
                    None,
                    q
                )
        headers = self.client.from_store('on_recv_response')[0][1]
        self.assertEqual(extract_from_headers(headers, ':status'), '501')

    @async_test
    async def test_bad_data(self):
        """
        Test that the server returns a 400 when the data payload is not a valid
        DNS packet.
        """
        if self.ARGS.post:
            with patch(
                    '__main__.Client.on_send_data',
                    new=Client._on_post_bad_body), \
                 patch(
                     '__main__.Client.on_start_request',
                    new=Client._on_start_request_bad_body
                 ):
                q = dns.message.make_query(qname='www.example.com', rdtype='A')
                with self.assertRaises(dns.name.BadLabelType):
                    await self.client.make_request(
                        None,
                        q
                    )
        else:
            with patch(
                    '__main__.Client.on_start_request',
                    new=Client._on_start_request_bad_dns):
                q = dns.message.make_query(qname='www.example.com', rdtype='A')

                with self.assertRaises(dns.name.BadLabelType):
                    await self.client.make_request(
                        None,
                        q
                    )
        headers = self.client.from_store('on_recv_response')[0][1]
        self.assertEqual(extract_from_headers(headers, ':status'), '400')


class ServerIntegrationPostTest(
        ServerIntegrationBaseClassTest, unittest.TestCase):

    def setUp(self):
        ServerIntegrationBaseClassTest.ARGS.post = True
        super().setUp()


class ServerIntegrationGetTest(
        ServerIntegrationBaseClassTest, unittest.TestCase):

    def setUp(self):
        ServerIntegrationBaseClassTest.ARGS.post = False
        super().setUp()

    @async_test
    async def test_head_method(self):
        """
        Test that when a HEAD method is sent to the server, 200 is returned.
        """
        with patch(
                '__main__.Client.on_start_request',
                new=Client._on_start_request_head_method):
            q = dns.message.make_query(qname='www.example.com', rdtype='A')
            with self.assertRaises(dns.message.ShortHeader):
                await self.client.make_request(
                    None,
                    q
                )

        headers = self.client.from_store('on_recv_response')[0][1]
        self.assertEqual(extract_from_headers(headers, ':status'), '200')
        self.assertEqual(
            extract_from_headers(headers, 'content-type'),
            constants.DOH_MEDIA_TYPE,
            'HEAD requests should return DOH content-type'
        )
        self.assertEqual(
            extract_from_headers(headers, 'content-length'),
            '0',
            'HEAD request should return content-length of 0'
        )
        self.assertIsNotNone(
            extract_from_headers(headers, 'cache-control'),
            'HEAD request should return cache-control header'
        )


def main():
    parser = utils.client_parser_base()
    parser.add_argument('args', nargs=argparse.REMAINDER)
    parser.add_argument(
        '--propagate-logs',
        action='store_true',
        help='Print logs generated by the client.')

    args = parser.parse_args()
    # HACK: pass arguments to `ServerIntegrationBaseClassTest` so we can access
    # them within the tests.
    ServerIntegrationBaseClassTest.ARGS = args

    unittest.main(
        argv=[sys.argv[0]] + args.args,
        testRunner=DOHTestRunner,
        verbosity=2)


if __name__ == '__main__':
    sys.exit(main())
