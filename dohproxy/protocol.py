#!/usr/bin/env python3
#
# Copyright (c) 2018-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
#

import dns.entropy


class DNSClientProtocol:
    def __init__(self, dnsq, queue):
        self.dnsq = dnsq
        self.dnsq.id = dns.entropy.random_16()
        self.queue = queue
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        print('Send: ID {} {}'.format(self.dnsq.id, self.dnsq.question[0]))
        self.transport.sendto(self.dnsq.to_wire())

    def datagram_received(self, data, addr):
        dnsr = dns.message.from_wire(data)
        print('Received: ID {} {}'.format(dnsr.id, dnsr.question[0]))
        dnsr.id = 0
        self.queue.put_nowait(dnsr)
        # print("Received:", dnsr)
        # print("Close the socket")
        self.transport.close()

    def error_received(self, exc):
        print('Error received:', exc)

    def connection_lost(self, exc):
        pass
