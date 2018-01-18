#!/usr/bin/env python3
#
# Copyright (c) 2018-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
#
import aiohttp.web
import asyncio
import dns.message
import dns.rcode

from dohproxy import constants, utils
from dohproxy.protocol import (
    DNSClientProtocol,
    DOHDNSException,
    DOHParamsException,
)


def parse_args():
    parser = utils.proxy_parser_base(port=80, secure=False)
    return parser.parse_args()


async def doh1handler(request):
    path, params = utils.extract_path_params(request.rel_url.path_qs)

    if request.method == 'GET':
        try:
            ct, body = utils.extract_ct_body(params)
        except DOHParamsException as e:
            return aiohttp.web.Response(status=400, body=e.body())
    else:
        body = request.content.read()
        ct = request.headers.get('content-type')

    if ct != constants.DOH_MEDIA_TYPE:
        return aiohttp.web.Response(
            status=415, body=b'Unsupported content type'
        )

    # Do actual DNS Query
    try:
        dnsq = utils.dns_query_from_body(body, debug=request.app.debug)
    except DOHDNSException as e:
        return aiohttp.web.Response(status=400, body=e.body())

    dnsq = dns.message.from_wire(body)
    request.app.logger.info(
        '[HTTPS] Received: ID {} Question {} Peer {}'.format(
            dnsq.id,
            dnsq.question[0],
            request.transport.get_extra_info('peername'),
        )
    )
    return await request.app.resolve(request, dnsq)


class DOHApplication(aiohttp.web.Application):

    def set_upstream_resolver(self, upstream_resolver):
        self.upstream_resolver = upstream_resolver

    async def resolve(self, request, dnsq):
        qid = dnsq.id
        queue = asyncio.Queue(maxsize=1)
        await self.loop.create_datagram_endpoint(
                lambda: DNSClientProtocol(dnsq, queue, logger=self.logger),
                remote_addr=(self.upstream_resolver, 53))

        self.logger.debug("Waiting for DNS response")
        try:
            dnsr = await asyncio.wait_for(queue.get(), 10)
            dnsr.id = qid
            queue.task_done()
            return self.on_answer(request, dnsr=dnsr)
        except asyncio.TimeoutError:
            self.logger.debug("Request timed out")
            return self.on_answer(request, dnsq=dnsq)

    def on_answer(self, request, dnsr=None, dnsq=None):
        headers = {}

        if dnsr is None:
            dnsr = dns.message.make_response(dnsq)
            dnsr.set_rcode(dns.rcode.SERVFAIL)
        elif len(dnsr.answer):
            ttl = min(r.ttl for r in dnsr.answer)
            headers['cache-control'] = 'max-age={}'.format(ttl)

        self.logger.info(
            '[HTTPS] Send: ID {} Question {} Peer {}'.format(
                dnsr.id,
                dnsr.question[0],
                request.transport.get_extra_info('peername')
            )
        )
        body = dnsr.to_wire()

        return aiohttp.web.Response(
            status=200,
            body=body,
            content_type=constants.DOH_MEDIA_TYPE,
        )


def main():
    args = parse_args()

    logger = utils.configure_logger('doh-httpproxy', args.level)
    app = DOHApplication(logger=logger, debug=args.debug)
    app.set_upstream_resolver(args.upstream_resolver)
    app.router.add_get(args.uri, doh1handler)
    aiohttp.web.run_app(app, host=args.listen_address, port=args.port)


if __name__ == '__main__':
    main()
