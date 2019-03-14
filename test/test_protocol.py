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
import struct
import unittest

from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from dohproxy import httpproxy
from dohproxy import utils

from unittest.mock import patch
from asyncio.base_events import BaseEventLoop
from dohproxy.server_protocol import DNSClient, DNSClientProtocolTCP, DNSClientProtocolUDP


class TCPTestCase(unittest.TestCase):

    def setUp(self):
        self.dnsq = dns.message.make_query(
            'www.example.com',
            dns.rdatatype.ANY)
        self.dnsr = dns.message.make_response(self.dnsq)
        self.response = self.dnsr.to_wire()

    @patch.object(DNSClientProtocolTCP, 'receive_helper')
    def test_single_valid(self, m_rcv):
        data = struct.pack('!H', len(self.response)) + self.response
        self.client_tcp = DNSClientProtocolTCP(self.dnsq, [], '10.0.0.0')
        self.client_tcp.data_received(data)
        m_rcv.assert_called_with(self.dnsr)

    @patch.object(DNSClientProtocolTCP, 'receive_helper')
    def test_two_valid(self, m_rcv):
        data = struct.pack('!H', len(self.response)) + self.response
        self.client_tcp = DNSClientProtocolTCP(self.dnsq, [], '10.0.0.0')
        self.client_tcp.data_received(data + data)
        m_rcv.assert_called_with(self.dnsr)
        self.assertEqual(m_rcv.call_count, 2)

    @patch.object(DNSClientProtocolTCP, 'receive_helper')
    def test_partial_valid(self, m_rcv):
        data = struct.pack('!H', len(self.response)) + self.response
        self.client_tcp = DNSClientProtocolTCP(self.dnsq, [], '10.0.0.0')
        self.client_tcp.data_received(data[0:5])
        m_rcv.assert_not_called()
        self.client_tcp.data_received(data[5:])
        m_rcv.assert_called_with(self.dnsr)

    @patch.object(DNSClientProtocolTCP, 'receive_helper')
    def test_len_byte(self, m_rcv):
        data = struct.pack('!H', len(self.response)) + self.response
        self.client_tcp = DNSClientProtocolTCP(self.dnsq, [], '10.0.0.0')
        self.client_tcp.data_received(data[0:1])
        m_rcv.assert_not_called()
        self.client_tcp.data_received(data[1:])
        m_rcv.assert_called_with(self.dnsr)

    @patch.object(DNSClientProtocolTCP, 'receive_helper')
    def test_complex(self, m_rcv):
        data = struct.pack('!H', len(self.response)) + self.response
        length = len(data)
        data = data * 3
        self.client_tcp = DNSClientProtocolTCP(self.dnsq, [], '10.0.0.0')
        self.client_tcp.data_received(data[0:length - 3])
        self.client_tcp.data_received(data[length - 3:length + 1])
        m_rcv.assert_called_with(self.dnsr)
        m_rcv.reset_mock()
        self.client_tcp.data_received(data[length + 1:2 * length])
        m_rcv.assert_called_with(self.dnsr)
        m_rcv.reset_mock()
        self.client_tcp.data_received(data[2 * length:])
        m_rcv.assert_called_with(self.dnsr)

    @patch.object(DNSClientProtocolTCP, 'receive_helper')
    def test_single_long(self, m_rcv):
        data = struct.pack('!H', len(self.response) - 3) + self.response
        self.client_tcp = DNSClientProtocolTCP(self.dnsq, [], '10.0.0.0')
        with self.assertRaises(dns.exception.FormError):
            self.client_tcp.data_received(data)

    @patch.object(DNSClientProtocolTCP, 'receive_helper')
    def test_single_short(self, m_rcv):
        data = struct.pack('!H', len(self.response) + 3) + self.response
        self.client_tcp = DNSClientProtocolTCP(self.dnsq, [], '10.0.0.0')
        self.client_tcp.data_received(data)
        m_rcv.assert_not_called()

class DNSClientTestCase(AioHTTPTestCase):

    def setUp(self):
        super().setUp()
        self.mylogger = utils.configure_logger('mylogger', 'ERROR')
        self.dnsclient = DNSClient("", 80, logger = self.mylogger)
        #self.dnsclient = DNSClient("", 80, logger = 'mylogger')
        self.dnsq = dns.message.make_query(
            qname='foo.example.com',
            rdtype='A',
        )

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

class DNSClientLoggerTestCase(DNSClientTestCase):

    def setup(self):
        super().setUp()

    @asynctest.patch('dohproxy.server_protocol.DNSClientProtocolTCP')
    @asynctest.patch.object(DNSClient, '_try_query')
    @unittest_run_loop
    async def test_get_DNSClientProtocolTCP_logger(self, Mocked_try_query, MockedDNSClientProtocolTCP):
        self.upstream_resolver = None
        self.upstream_port = None
        try:
            await self.dnsclient.query_tcp(self.dnsq, "127.0.0.1", timeout=0)
        except:
            pass
        Mocked_try_query.return_value = self.dnsq
        expectedlogger = utils.configure_logger(name='mylogger', level='ERROR')
        self.assertEqual(MockedDNSClientProtocolTCP.call_args[1]['logger'], expectedlogger)


    @asynctest.patch('dohproxy.server_protocol.DNSClientProtocolUDP')
    @asynctest.patch.object(DNSClient, '_try_query')
    @unittest_run_loop
    async def test_get_DNSClientProtocolUDP_logger(self, Mocked_try_query, MockedDNSClientProtocolUDP):
        self.upstream_resolver = None
        self.upstream_port = None
        try:
            await self.dnsclient.query_udp(self.dnsq, "127.0.0.1", timeout=0)
        except:
            pass
        Mocked_try_query.return_value = self.dnsq
        expectedlogger = utils.configure_logger(name='mylogger', level='ERROR')
        self.assertEqual(MockedDNSClientProtocolUDP.call_args[1]['logger'], expectedlogger)
