#!/usr/bin/env python3
#
# Copyright (c) 2018-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
#

import asyncio
import os
import unittest

import asynctest
import dns
import dns.message
from dohproxy import client_protocol, utils

TEST_TIMEOUT = 3.0
TRAVIS_TIMEOUT = 15.0

METHOD_GET = 1
METHOD_POST = 2
METHOD_BOTH = 3


def known_servers():
    '''
    List of servers taken from
    https://github.com/curl/curl/wiki/DNS-over-HTTPS#publicly-available-servers
    '''
    return [
        # Name, Domain, endpoint
        ('Google', 'dns.google', '/dns-query', METHOD_BOTH),
        ('Cloudflare', 'cloudflare-dns.com', '/dns-query', METHOD_BOTH),
        (
            'CleanBrowsing', 'doh.cleanbrowsing.org',
            '/doh/family-filter/', METHOD_BOTH
        ),
        # Currently off
        # ('@chantra', 'dns.dnsoverhttps.net', '/dns-query', METHOD_BOTH),
        ('@jedisct1', 'doh.crypto.sx', '/dns-query', METHOD_GET),
        # Timeout
        # ('SecureDNS.eu', 'doh.securedns.eu', '/dns-query', METHOD_BOTH),
        ('BlahDNS.com JP', 'doh-jp.blahdns.com', '/dns-query', METHOD_BOTH),
        ('BlahDNS.com DE', 'doh-de.blahdns.com', '/dns-query', METHOD_BOTH),
        (
            'NekomimiRouter.com', 'dns.dns-over-https.com',
            '/dns-query', METHOD_BOTH
        ),
    ]


def build_query(qname, qtype):
    dnsq = dns.message.make_query(
        qname=qname,
        rdtype=qtype,
    )
    dnsq.id = 0
    return dnsq


class Client(client_protocol.StubServerProtocol):
    result = None

    def on_answer(self, addr, msg):
        self.result = dns.message.from_wire(msg)


class TestKnownServers(asynctest.TestCase):
    def setUp(self):
        super().setUp()
        # ALPN requires >=openssl-1.0.2
        # NPN requires >=openssl-1.0.1
        self.test_timeout = TEST_TIMEOUT
        if os.getenv('TRAVIS'):
            self.test_timeout = TRAVIS_TIMEOUT
            for fn in ['set_alpn_protocols']:
                patcher = unittest.mock.patch('ssl.SSLContext.{0}'.format(fn))
                patcher.start()
                self.addCleanup(patcher.stop)

    async def _test_servers(self, post=False):
        for name, domain, uri, methods in known_servers():
            if post and not methods & METHOD_POST:
                continue
            if not post and not methods & METHOD_GET:
                continue
            with self.subTest(name):
                arglist = [
                    '--domain',
                    domain,
                    '--uri',
                    uri,
                ]
                if post:
                    arglist.append('--post')
                parser = utils.client_parser_base()
                args = parser.parse_args(arglist)
                logger = utils.configure_logger('doh-integrationtest')
                c = Client(args=args, logger=logger)
                fut = c.make_request(None, build_query(
                    qname=domain, qtype="A"))
                try:
                    await asyncio.wait_for(fut, self.test_timeout)
                except asyncio.TimeoutError:
                    raise unittest.SkipTest("%s Timeouted" % name)
                self.assertEqual(1, len(c.result.question))
                self.assertGreater(len(c.result.answer), 0)

    async def test_servers_get(self):
        await self._test_servers(post=False)

    async def test_servers_post(self):
        await self._test_servers(post=True)
