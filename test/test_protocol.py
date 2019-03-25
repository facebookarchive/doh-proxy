#!/usr/bin/env python3
#
# Copyright (c) 2018-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
#
import asyncio
import dns
import dns.message
import struct
import unittest

from unittest.mock import patch
from dohproxy.server_protocol import DNSClientProtocolTCP


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
        client_tcp = DNSClientProtocolTCP(self.dnsq, [], '10.0.0.0')
        client_tcp.data_received(data)
        m_rcv.assert_called_with(self.dnsr)

    @patch.object(DNSClientProtocolTCP, 'receive_helper')
    def test_two_valid(self, m_rcv):
        data = struct.pack('!H', len(self.response)) + self.response
        client_tcp = DNSClientProtocolTCP(self.dnsq, [], '10.0.0.0')
        client_tcp.data_received(data + data)
        m_rcv.assert_called_with(self.dnsr)
        self.assertEqual(m_rcv.call_count, 2)

    @patch.object(DNSClientProtocolTCP, 'receive_helper')
    def test_partial_valid(self, m_rcv):
        data = struct.pack('!H', len(self.response)) + self.response
        client_tcp = DNSClientProtocolTCP(self.dnsq, [], '10.0.0.0')
        client_tcp.data_received(data[0:5])
        m_rcv.assert_not_called()
        client_tcp.data_received(data[5:])
        m_rcv.assert_called_with(self.dnsr)

    @patch.object(DNSClientProtocolTCP, 'receive_helper')
    def test_len_byte(self, m_rcv):
        data = struct.pack('!H', len(self.response)) + self.response
        client_tcp = DNSClientProtocolTCP(self.dnsq, [], '10.0.0.0')
        client_tcp.data_received(data[0:1])
        m_rcv.assert_not_called()
        client_tcp.data_received(data[1:])
        m_rcv.assert_called_with(self.dnsr)

    @patch.object(DNSClientProtocolTCP, 'receive_helper')
    def test_complex(self, m_rcv):
        data = struct.pack('!H', len(self.response)) + self.response
        length = len(data)
        data = data * 3
        client_tcp = DNSClientProtocolTCP(self.dnsq, [], '10.0.0.0')
        client_tcp.data_received(data[0:length - 3])
        client_tcp.data_received(data[length - 3:length + 1])
        m_rcv.assert_called_with(self.dnsr)
        m_rcv.reset_mock()
        client_tcp.data_received(data[length + 1:2 * length])
        m_rcv.assert_called_with(self.dnsr)
        m_rcv.reset_mock()
        client_tcp.data_received(data[2 * length:])
        m_rcv.assert_called_with(self.dnsr)

    @patch.object(DNSClientProtocolTCP, 'receive_helper')
    def test_single_long(self, m_rcv):
        data = struct.pack('!H', len(self.response) - 3) + self.response
        client_tcp = DNSClientProtocolTCP(self.dnsq, [], '10.0.0.0')
        with self.assertRaises(dns.exception.FormError):
            client_tcp.data_received(data)

    @patch.object(DNSClientProtocolTCP, 'receive_helper')
    def test_single_short(self, m_rcv):
        data = struct.pack('!H', len(self.response) + 3) + self.response
        client_tcp = DNSClientProtocolTCP(self.dnsq, [], '10.0.0.0')
        client_tcp.data_received(data)
        m_rcv.assert_not_called()

    def test_cancelled_future(self):
        """Ensures that cancelled futures are handled appropriately."""
        data = struct.pack('!H', len(self.response)) + self.response

        mock_future = unittest.mock.MagicMock(asyncio.Future)
        client_tcp = DNSClientProtocolTCP(
            self.dnsq, mock_future, '10.0.0.0')
        client_tcp.time_stamp = 1000000

        # If the future is cancelled, set_result raises InvalidStateError.
        mock_future.set_result.side_effect = (
            asyncio.InvalidStateError('CANCELLED: <Future cancelled>')
        )
        client_tcp.data_received(data)
