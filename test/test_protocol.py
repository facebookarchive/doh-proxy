#!/usr/bin/env python3
#
# Copyright (c) 2018-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
#
import dns
import dns.message
import struct
import unittest

from unittest.mock import patch
from dohproxy.server_protocol import DNSClientProtocolTCP


class TCPTestCase(unittest.TestCase):

    def setUp(self):
        """
        prepare the dns response
        """
        self.dnsq = dns.message.make_query(
            'www.example.com',
            dns.rdatatype.ANY)
        self.dnsr = dns.message.make_response(self.dnsq)
        self.response = self.dnsr.to_wire()

    def r_receive_helper(self, dnsr):
        """
        fut attribute as a list to store the answer from receive helper
        """
        self.fut.append(dnsr)

    def r_eof_received(self):
        """
        here we raise a general expection when we discard broken message
        """
        if len(self.buffer) > 0:
            raise Exception

    @patch.object(DNSClientProtocolTCP, 'receive_helper', new=r_receive_helper)
    @patch.object(DNSClientProtocolTCP, 'eof_received', new=r_eof_received)
    def test_single_valid(self):
        """
        only one unbroken message is sent
        """
        data = struct.pack("!H", len(self.response)) + self.response
        self.client_tcp = DNSClientProtocolTCP(self.dnsq, [], '10.0.0.0')
        self.client_tcp.data_received(data)
        self.client_tcp.eof_received()
        ans = self.client_tcp.fut
        self.assertEqual(ans, [self.dnsr])

    @patch.object(DNSClientProtocolTCP, 'receive_helper', new=r_receive_helper)
    @patch.object(DNSClientProtocolTCP, 'eof_received', new=r_eof_received)
    def test_two_valid(self):
        """
        two unbroken messages
        """
        data = struct.pack("!H", len(self.response)) + self.response
        self.client_tcp = DNSClientProtocolTCP(self.dnsq, [], '10.0.0.0')
        self.client_tcp.data_received(data + data)
        self.client_tcp.eof_received()
        ans = self.client_tcp.fut
        self.assertEqual(ans, [self.dnsr, self.dnsr])

    @patch.object(DNSClientProtocolTCP, 'receive_helper', new=r_receive_helper)
    @patch.object(DNSClientProtocolTCP, 'eof_received', new=r_eof_received)
    def test_partial_valid(self):
        """
        slice the messages but with entire len bytes
        """
        data = struct.pack("!H", len(self.response)) + self.response
        self.client_tcp = DNSClientProtocolTCP(self.dnsq, [], '10.0.0.0')
        self.client_tcp.data_received(data[0:5])
        self.client_tcp.data_received(data[5:])
        self.client_tcp.eof_received()
        ans = self.client_tcp.fut
        self.assertEqual(ans, [self.dnsr])

    @patch.object(DNSClientProtocolTCP, 'receive_helper', new=r_receive_helper)
    @patch.object(DNSClientProtocolTCP, 'eof_received', new=r_eof_received)
    def test_len_byte(self):
        """
        the len bytes is divided into two responses
        """
        data = struct.pack("!H", len(self.response)) + self.response
        self.client_tcp = DNSClientProtocolTCP(self.dnsq, [], '10.0.0.0')
        self.client_tcp.data_received(data[0:1])
        self.client_tcp.data_received(data[1:])
        self.client_tcp.eof_received()
        ans = self.client_tcp.fut
        self.assertEqual(ans, [self.dnsr])

    @patch.object(DNSClientProtocolTCP, 'receive_helper', new=r_receive_helper)
    @patch.object(DNSClientProtocolTCP, 'eof_received', new=r_eof_received)
    def test_complex(self):
        """
        more complex case with 3 messages
        """
        data = struct.pack("!H", len(self.response)) + self.response
        length = len(data)
        data = data * 3
        self.client_tcp = DNSClientProtocolTCP(self.dnsq, [], '10.0.0.0')
        self.client_tcp.data_received(data[0:length - 3])
        self.client_tcp.data_received(data[length - 3:length + 1])
        self.client_tcp.data_received(data[length + 1:2 * length])
        self.client_tcp.data_received(data[2 * length:])
        self.client_tcp.eof_received()
        ans = self.client_tcp.fut
        self.assertEqual(ans, [self.dnsr, self.dnsr, self.dnsr])

    @patch.object(DNSClientProtocolTCP, 'receive_helper', new=r_receive_helper)
    @patch.object(DNSClientProtocolTCP, 'eof_received', new=r_eof_received)
    def test_single_long(self):
        """
        the message is acutally longer than expected length
        """
        data = struct.pack("!H", len(self.response) - 3) + self.response
        self.client_tcp = DNSClientProtocolTCP(self.dnsq, [], '10.0.0.0')
        with self.assertRaises(dns.exception.FormError):
            self.client_tcp.data_received(data)
            self.client_tcp.eof_received()
        ans = self.client_tcp.fut
        self.assertEqual(ans, [])

    @patch.object(DNSClientProtocolTCP, 'receive_helper', new=r_receive_helper)
    @patch.object(DNSClientProtocolTCP, 'eof_received', new=r_eof_received)
    def test_single_short(self):
        """
        the message is actually shorter than expected length
        """
        data = struct.pack("!H", len(self.response) + 3) + self.response
        self.client_tcp = DNSClientProtocolTCP(self.dnsq, [], '10.0.0.0')
        with self.assertRaises(Exception):
            self.client_tcp.data_received(data)
            self.client_tcp.eof_received()
        ans = self.client_tcp.fut
        self.assertEqual(ans, [])


if __name__ == '__main__':
    unittest.main()
