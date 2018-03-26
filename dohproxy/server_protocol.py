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
import time
import asyncio

from dohproxy import utils


class DOHException(Exception):

    def body(self):
        return self.args[0]


class DOHParamsException(DOHException):
    pass


class DOHDNSException(DOHException):
    pass


class DNSClientProtocol(asyncio.Protocol):

    def __init__(self, dnsq, fut, clientip, logger=None):
        self.dnsq = dnsq
        self.transport = None
        self.fut = fut
        self.logger = logger
        self.clientip = clientip
        if logger is None:
            self.logger = utils.configure_logger('DNSClientProtocol', 'DEBUG')

    def connection_made(self, transport):
        self.connection_helper(transport)
        self.transport.sendto(self.dnsq.to_wire())

    def datagram_received(self, data, addr):
        dnsr = dns.message.from_wire(data)
        interval = int((time.time() - self.time_stamp) * 1000)
        self.logger.info(
            '[DNS] {} {} {}ms'.format(
                self.clientip,
                utils.dnsans2log(dnsr),
                interval
            )
        )
        self.fut.set_result(dnsr)
        self.transport.close()

    def error_received(self, exc):
        print('Error received:', exc)

    def connection_lost(self, exc):
        pass

    def connection_helper(self, transport):
        self.transport = transport
        self.dnsq.id = dns.entropy.random_16()
        self.logger.info(
            '[DNS] {} {}'.format(
                self.clientip,
                utils.dnsquery2log(self.dnsq)
            )
        )
        self.time_stamp = time.time()


class DNSClientProtocolTCP(DNSClientProtocol):

    def connection_made(self, transport):
        self.connection_helper(transport)
        self.transport.write(self.dnsq.to_wire())
