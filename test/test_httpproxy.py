#!/usr/bin/env python3
#
# Copyright (c) 2018-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
#

import aiohttp
import aiohttp_remotes
import asynctest
import dns.message
import logging

from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from dohproxy import constants
from dohproxy import httpproxy
from dohproxy import utils
from dohproxy import server_protocol
from dohproxy.server_protocol import DNSClient
from unittest.mock import MagicMock, patch


def echo_dns_q(q):
    return aiohttp.web.Response(
        status=200,
        body=q.to_wire(),
        content_type=constants.DOH_MEDIA_TYPE,
    )


class HTTPProxyTestCase(AioHTTPTestCase):
    def setUp(self):
        super().setUp()
        self.endpoint = '/dns'
        self.dnsq = dns.message.make_query(
            qname='foo.example.com',
            rdtype='A',
        )
        self.dnsq.id = 0

    def get_args(self):
        return [
            '--listen-port',
            '0',
            '--level',
            'DEBUG',
            '--listen-address',
            '127.0.0.1',
            '--uri',
            '/dns',
            '--trusted',
        ]

    async def get_application(self):
        """
        Override the get_app method to return your application.
        """
        parser, args = httpproxy.parse_args(self.get_args())
        return httpproxy.get_app(args)


class HTTPProxyGETTestCase(HTTPProxyTestCase):
    def setUp(self):
        super().setUp()
        self.method = 'GET'

    @asynctest.patch.object(httpproxy.DOHApplication, 'resolve')
    @unittest_run_loop
    async def test_get_valid_request(self, resolve):
        """ Test that when we run a valid GET request, resolve will be called
        and returns some content, here echoes the request.
        """
        resolve.return_value = echo_dns_q(self.dnsq)
        params = utils.build_query_params(self.dnsq.to_wire())
        request = await self.client.request(
            self.method, self.endpoint, params=params)
        self.assertEqual(request.status, 200)
        content = await request.read()

        self.assertEqual(self.dnsq, dns.message.from_wire(content))

    @asynctest.patch.object(httpproxy.DOHApplication, 'resolve')
    @unittest_run_loop
    async def test_get_request_bad_content_type(self, resolve):
        """ Test that when an invalid content-type is provided, we return 200.
        content-type is not used in GET request anymore, so it will default to
        'application/dns-message'
        """
        resolve.return_value = echo_dns_q(self.dnsq)
        params = utils.build_query_params(self.dnsq.to_wire())
        params['ct'] = 'bad/type'
        request = await self.client.request(
            self.method, self.endpoint, params=params)
        self.assertEqual(request.status, 200)
        content = await request.read()
        self.assertEqual(self.dnsq, dns.message.from_wire(content))

    @asynctest.patch.object(httpproxy.DOHApplication, 'resolve')
    @unittest_run_loop
    async def test_get_request_no_content_type(self, resolve):
        """ Test that when no ct parameter, we accept the query.
        content-type is not used in GET request anymore, so it will default to
        'application/dns-message'
        """
        resolve.return_value = echo_dns_q(self.dnsq)
        params = utils.build_query_params(self.dnsq.to_wire())
        request = await self.client.request(
            self.method, self.endpoint, params=params)
        self.assertEqual(request.status, 200)
        content = await request.read()
        self.assertEqual(self.dnsq, dns.message.from_wire(content))

    @unittest_run_loop
    async def test_get_request_empty_body(self):
        """ Test that when an empty body is provided, we return 400.
        """
        params = utils.build_query_params(self.dnsq.to_wire())
        params[constants.DOH_DNS_PARAM] = ''
        request = await self.client.request(
            self.method, self.endpoint, params=params)
        self.assertEqual(request.status, 400)
        content = await request.read()
        self.assertEqual(content, b'Missing Body')

    @unittest_run_loop
    async def test_get_request_bad_dns_request(self):
        """ Test that when an invalid body is provided, we return 400.
        """
        params = utils.build_query_params(self.dnsq.to_wire())
        params[constants.DOH_DNS_PARAM] = 'dummy'
        request = await self.client.request(
            self.method, self.endpoint, params=params)
        self.assertEqual(request.status, 400)
        content = await request.read()
        self.assertEqual(content, b'Invalid Body Parameter')


class HTTPProxyPOSTTestCase(HTTPProxyTestCase):
    def setUp(self):
        super().setUp()
        self.method = 'POST'

    def make_header(self):
        return {'content-type': constants.DOH_MEDIA_TYPE}

    def make_body(self, q):
        return q.to_wire()

    @asynctest.patch.object(httpproxy.DOHApplication, 'resolve')
    @unittest_run_loop
    async def test_post_valid_request(self, resolve):
        """ Test that when we run a valid POST request, resolve will be called
        and returns some content, here echoes the request.
        """
        resolve.return_value = echo_dns_q(self.dnsq)
        request = await self.client.request(
            self.method,
            self.endpoint,
            headers=self.make_header(),
            data=self.make_body(self.dnsq))

        self.assertEqual(request.status, 200)
        content = await request.read()

        self.assertEqual(self.dnsq, dns.message.from_wire(content))

    @unittest_run_loop
    async def test_post_request_no_content_type(self):
        """ Test that when no content-type is provided, we return 415.
        """
        request = await self.client.request(
            self.method,
            self.endpoint,
            headers={},
            data=self.make_body(self.dnsq))

        self.assertEqual(request.status, 415)
        content = await request.read()

        self.assertEqual(content, b'Unsupported content type')

    @unittest_run_loop
    async def test_post_request_bad_content_type(self):
        """ Test that when an invalid content-type is provided, we return 415.
        """
        request = await self.client.request(
            self.method,
            self.endpoint,
            headers={'content-type': 'bad/type'},
            data=self.make_body(self.dnsq))

        self.assertEqual(request.status, 415)
        content = await request.read()
        self.assertEqual(content, b'Unsupported content type')

    @unittest_run_loop
    async def test_post_request_empty_body(self):
        """ Test that when an empty body is provided, we return 400.
        """
        request = await self.client.request(
            self.method,
            self.endpoint,
            headers=self.make_header(),
        )

        self.assertEqual(request.status, 400)
        content = await request.read()
        self.assertEqual(content, b'Malformed DNS query')

    @unittest_run_loop
    async def test_post_request_bad_dns_request(self):
        """ Test that when an invalid dns request is provided, we return 400.
        """
        request = await self.client.request(
            self.method,
            self.endpoint,
            headers=self.make_header(),
            data='dummy',
        )

        self.assertEqual(request.status, 400)
        content = await request.read()
        self.assertEqual(content, b'Malformed DNS query')


class HTTPProxyXForwardedModeTestCase(HTTPProxyTestCase):
    """ Trusted parameter is set by default to [::1, 127.0.0.1].
    See httpproxy.parse_args
    """

    def setUp(self):
        super().setUp()

    def get_args(self):
        return [
            '--listen-port',
            '0',
            '--level',
            'DEBUG',
            '--listen-address',
            '127.0.0.1',
            '--uri',
            '/dns',
        ]

    @asynctest.patch.object(aiohttp_remotes, 'XForwardedStrict')
    @asynctest.patch.object(aiohttp_remotes, 'XForwardedRelaxed')
    @unittest_run_loop
    async def test_xforwarded_mode_with_trusted_hosts(
            self, mock_xforwarded_relaxed, mock_xforwarded_strict):
        """ Test that when the aiohttp app have some trusted hosts specified at
        initialization, the XForwardedStrict method is applied.
        """
        args = self.get_args()
        args.extend(['--trusted', ['::1', '127.0.0.1']])
        parser, args = httpproxy.parse_args(self.get_args())
        httpproxy.get_app(args)

        not mock_xforwarded_relaxed.called
        mock_xforwarded_strict.called

    @asynctest.patch.object(aiohttp_remotes, 'XForwardedStrict')
    @asynctest.patch.object(aiohttp_remotes, 'XForwardedRelaxed')
    @unittest_run_loop
    async def test_xforwarded_mode_without_trusted_hosts(
            self, mock_xforwarded_relaxed, mock_xforwarded_strict):
        """ Test that when the aiohttp app have some trusted hosts specified at
        initialization, the XForwardedStrict method is applied.
        """
        args = self.get_args()
        args.extend(['--trusted'])
        parser, args = httpproxy.parse_args(self.get_args())
        httpproxy.get_app(args)

        mock_xforwarded_relaxed.called
        not mock_xforwarded_strict.called


async def async_magic():
    pass
# make MagicMock could be used in 'await' expression
MagicMock.__await__ = lambda x: async_magic().__await__()


class DNSClientLoggerTestCase(HTTPProxyTestCase):
    # This class mainly helps verify logger's propagation.

    def setUp(self):
        super().setUp()

    @asynctest.patch.object(server_protocol.DNSClient, 'query')
    @patch.object(httpproxy.DOHApplication, 'on_answer')
    @asynctest.patch('dohproxy.httpproxy.DNSClient')
    @unittest_run_loop
    async def test_mock_dnsclient_assigned_logger(self, MockedDNSClient,
                                                  Mockedon_answer,
                                                  Mockedquery):
        """ Test that when MockedDNSClient is created with the doh-httpproxy
        logger and DEBUG level
        """
        Mockedquery.return_value = self.dnsq
        Mockedon_answer.return_value = aiohttp.web.Response(status=200,
                                                            body=b'Done')
        params = utils.build_query_params(self.dnsq.to_wire())
        request = await self.client.request(
            'GET', self.endpoint, params=params)
        request.remote = "127.0.0.1"
        app = await self.get_application()
        await app.resolve(request, self.dnsq)

        mylogger = utils.configure_logger(name='doh-httpproxy', level='DEBUG')
        MockedDNSClient.assert_called_with(app.upstream_resolver,
                                           app.upstream_port,
                                           logger=mylogger)

    def test_dnsclient_none_logger(self):
        """ Test that when DNSClient is created without a logger,
        The default logger and default level 'DEBUG' should be used.
        """
        dnsclient = DNSClient("", 80)
        self.assertEqual(dnsclient.logger.level, 10)  # DEBUG's level is 10
        self.assertEqual(dnsclient.logger.name, 'DNSClient')

    def test_dnsclient_assigned_logger(self):
        """ Test that when DNSClient is created with a logger,
        This logger and its corresponding level should be used.
        """
        mylogger = logging.getLogger("mylogger")
        level = 'ERROR'
        mylogger.setLevel(level)

        dnsclient = DNSClient("", 80, logger=mylogger)
        self.assertEqual(dnsclient.logger.level, 40)  # ERROR's level is 40
        self.assertEqual(dnsclient.logger.name, 'mylogger')
