#!/usr/bin/env python3
#
# Copyright (c) 2018-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
#

import asyncio
import asynctest
import dns
import dns.message
import os
import unittest

from dohproxy import client_protocol, utils

TEST_TIMEOUT = 3.0
TRAVIS_TIMEOUT = 15.0


def known_servers():
    '''
    List of servers taken from
    https://github.com/curl/curl/wiki/DNS-over-HTTPS#publicly-available-servers
    '''
    return [
        # Name, Domain, endpoint
        ('Google', 'dns.google.com', '/experimental'),
        ('Cloudflare', 'cloudflare-dns.com', '/dns-query'),
        ('CleanBrowsing', 'doh.cleanbrowsing.org', '/doh/family-filter/'),
        ('@chantra', 'dns.dnsoverhttps.net', '/dns-query'),
        ('@jedisct1', 'doh.crypto.sx', '/dns-query'),
        # Timeout
        # ('SecureDNS.eu', 'doh.securedns.eu', '/dns-query'),
        ('BlahDNS.com JP', 'doh-jp.blahdns.com', '/dns-query'),
        ('BlahDNS.com DE', 'doh-de.blahdns.com', '/dns-query'),
        ('NekomimiRouter.com', 'dns.dns-over-https.com', '/dns-query'),
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
        for name, domain, uri in known_servers():
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
