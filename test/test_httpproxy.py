#!/usr/bin/env python3
#
# Copyright (c) 2018-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
#

import aiohttp
import asynctest
import dns.message

from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from dohproxy import constants
from dohproxy import httpproxy
from dohproxy import utils


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
            '--listen-port', '0',
            '--level', 'DEBUG',
            '--listen-address', '127.0.0.1',
            '--uri', '/dns',
        ]

    async def get_application(self):
        """
        Override the get_app method to return your application.
        """
        return httpproxy.get_app(httpproxy.parse_args(self.get_args()))


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
        resolve.return_value = aiohttp.web.Response(
            status=200,
            body=self.dnsq.to_wire(),
            content_type=constants.DOH_MEDIA_TYPE,
        )
        params = utils.build_query_params(self.dnsq.to_wire())
        request = await self.client.request(
            self.method,
            self.endpoint,
            params=params)
        self.assertEqual(request.status, 200)
        content = await request.read()

        self.assertEqual(self.dnsq, dns.message.from_wire(content))

    @unittest_run_loop
    async def test_get_request_no_content_type(self):
        """ Test that when no ct parameter, we fail with missing content type
        parameter.
        """
        params = utils.build_query_params(self.dnsq.to_wire())
        del params[constants.DOH_CONTENT_TYPE_PARAM]
        request = await self.client.request(
            self.method,
            self.endpoint,
            params=params)
        self.assertEqual(request.status, 400)
        content = await request.read()
        self.assertEqual(content, b'Missing Content Type Parameter')

    @unittest_run_loop
    async def test_get_request_bad_content_type(self):
        """ Test that when an invalid content-type is provided, we return 415.
        """
        params = utils.build_query_params(self.dnsq.to_wire())
        params[constants.DOH_CONTENT_TYPE_PARAM] = 'bad/type'
        request = await self.client.request(
            self.method,
            self.endpoint,
            params=params)
        self.assertEqual(request.status, 415)
        content = await request.read()
        self.assertEqual(content, b'Unsupported content type')

    @unittest_run_loop
    async def test_get_request_empty_body(self):
        """ Test that when an empty body is provided, we return 400.
        """
        params = utils.build_query_params(self.dnsq.to_wire())
        params[constants.DOH_DNS_PARAM] = ''
        request = await self.client.request(
            self.method,
            self.endpoint,
            params=params)
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
            self.method,
            self.endpoint,
            params=params)
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
        resolve.return_value = aiohttp.web.Response(
            status=200,
            body=self.dnsq.to_wire(),
            content_type=constants.DOH_MEDIA_TYPE,
        )
        request = await self.client.request(
            self.method, self.endpoint,
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
            self.method, self.endpoint,
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
            self.method, self.endpoint,
            headers={constants.DOH_CONTENT_TYPE_PARAM: 'bad/type'},
            data=self.make_body(self.dnsq))

        self.assertEqual(request.status, 415)
        content = await request.read()
        self.assertEqual(content, b'Unsupported content type')

    @unittest_run_loop
    async def test_post_request_empty_body(self):
        """ Test that when an empty body is provided, we return 400.
        """
        request = await self.client.request(
            self.method, self.endpoint,
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
            self.method, self.endpoint,
            headers=self.make_header(),
            data='dummy',
        )

        self.assertEqual(request.status, 400)
        content = await request.read()
        self.assertEqual(content, b'Malformed DNS query')
