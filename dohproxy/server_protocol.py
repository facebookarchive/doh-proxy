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

from dohproxy import utils


class DOHException(Exception):

    def body(self):
        return self.args[0]


class DOHParamsException(DOHException):
    pass


class DOHDNSException(DOHException):
    pass


class DNSClientProtocol:
    def __init__(self, dnsq, queue, clientip, logger=None):
        self.dnsq = dnsq
        self.queue = queue
        self.transport = None
        self.logger = logger
        self.clientip = clientip
        if logger is None:
            self.logger = utils.configure_logger('DNSClientProtocol', 'DEBUG')

    def connection_made(self, transport):
        self.transport = transport
        self.dnsq.id = dns.entropy.random_16()
        self.logger.info(
            '[DNS] {} {}'.format(
                self.clientip,
                utils.dnsquery2log(self.dnsq)
            )
        )
        self.time_stamp = time.time()
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
        self.queue.put_nowait(dnsr)
        self.transport.close()

    def error_received(self, exc):
        print('Error received:', exc)

    def connection_lost(self, exc):
        pass
