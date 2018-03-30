#!/usr/bin/env python3
#
# Copyright (c) 2018-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
#
import asyncio
import dns.entropy
import dns.message
import struct
import time

from dohproxy import utils


class DOHException(Exception):

    def body(self):
        return self.args[0]


class DOHParamsException(DOHException):
    pass


class DOHDNSException(DOHException):
    pass


class DNSClient():

    DEFAULT_TIMEOUT = 10

    def __init__(self, upstream_resolver, upstream_port):
        self.loop = asyncio.get_event_loop()
        self.upstream_resolver = upstream_resolver
        self.upstream_port = upstream_port

    async def query(self, dnsq, clientip, timeout=DEFAULT_TIMEOUT):
        dnsr = await self.query_udp(dnsq, clientip, timeout)
        if dnsr is None or (dnsr.flags & dns.flags.TC):
            dnsr = await self.query_tcp(dnsq, clientip, timeout)
        return dnsr

    async def query_udp(self, dnsq, clientip, timeout=DEFAULT_TIMEOUT):
        qid = dnsq.id
        fut = asyncio.Future()
        await self.loop.create_datagram_endpoint(
            lambda: DNSClientProtocolUDP(dnsq, fut, clientip),
            remote_addr=(self.upstream_resolver, self.upstream_port))
        return await self._try_query(fut, qid, timeout)

    async def query_tcp(self, dnsq, clientip, timeout=DEFAULT_TIMEOUT):
        qid = dnsq.id
        fut = asyncio.Future()
        await self.loop.create_connection(
            lambda: DNSClientProtocolTCP(dnsq, fut, clientip),
            self.upstream_resolver, self.upstream_port)
        return await self._try_query(fut, qid, timeout)

    async def _try_query(self, fut, qid, timeout):
        try:
            await asyncio.wait_for(fut, timeout)
            dnsr = fut.result()
            dnsr.id = qid
        except asyncio.TimeoutError:
            self.logger.debug("Request timed out")
            dnsr = None
        finally:
            return dnsr


class DNSClientProtocol(asyncio.Protocol):

    def __init__(self, dnsq, fut, clientip, logger=None):
        self.dnsq = dnsq
        self.transport = None
        self.fut = fut
        self.logger = logger
        self.clientip = clientip
        if logger is None:
            self.logger = utils.configure_logger('DNSClientProtocol', 'DEBUG')

    def error_received(self, exc):
        print('Error received:', exc)

    def connection_lost(self, exc):
        pass

    def connection_made(self, transport):
        raise NotImplementedError("This is the base class")

    def data_received(self, data):
        raise NotImplementedError("This is the base class")

    def datagram_received(self, data, addr):
        raise NotImplementedError("This is the base class")

    def send_helper(self, transport):
        self.transport = transport
        self.dnsq.id = dns.entropy.random_16()
        self.logger.info(
            '[DNS] {} {}'.format(
                self.clientip,
                utils.dnsquery2log(self.dnsq)
            )
        )
        self.time_stamp = time.time()

    def receive_helper(self, dnsr):
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


class DNSClientProtocolUDP(DNSClientProtocol):

    def connection_made(self, transport):
        self.send_helper(transport)
        self.transport.sendto(self.dnsq.to_wire())

    def datagram_received(self, data, addr):
        dnsr = dns.message.from_wire(data)
        self.receive_helper(dnsr)


class DNSClientProtocolTCP(DNSClientProtocol):

    def connection_made(self, transport):
        self.send_helper(transport)
        msg = self.dnsq.to_wire()
        tcpmsg = struct.pack("!H", len(msg)) + msg
        self.transport.write(tcpmsg)

    def data_received(self, data):
        dnsr = dns.message.from_wire(data[2:])
        self.receive_helper(dnsr)
