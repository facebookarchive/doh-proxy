#!/usr/bin/env python3
#
# Copyright (c) 2018-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
#

import dns.entropy
import dns.message


from dohproxy import utils


class DOHException(Exception):

    def body(self):
        return self.args[0]


class DOHParamsException(DOHException):
    pass


class DOHDNSException(DOHException):
    pass


class DNSClientProtocol:
    def __init__(self, dnsq, queue, logger=None):
        self.dnsq = dnsq
        self.queue = queue
        self.transport = None
        self.logger = logger
        if logger is None:
            self.logger = utils.configure_logger('DNSClientProtocol', 'DEBUG')

    def connection_made(self, transport):
        self.transport = transport
        self.dnsq.id = dns.entropy.random_16()
        self.logger.info('[DNS] Send: {}'.format(utils.dnsmsg2log(self.dnsq)))
        self.transport.sendto(self.dnsq.to_wire())

    def datagram_received(self, data, addr):
        dnsr = dns.message.from_wire(data)
        self.logger.info('[DNS] Received: {}'.format(utils.dnsmsg2log(dnsr)))
        self.queue.put_nowait(dnsr)
        self.transport.close()

    def error_received(self, exc):
        print('Error received:', exc)

    def connection_lost(self, exc):
        pass
