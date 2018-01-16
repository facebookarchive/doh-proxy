#!/usr/bin/env python3
#
# Copyright (c) 2018-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
#
import aiohttp.web
import argparse
import asyncio
import dns.message
import dns.rcode

from dohproxy import constants, utils
from dohproxy.protocol import DNSClientProtocol


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--listen-address',
        default=None,
        help='The address the proxy should listen on. Default: [%(default)s]'
    )
    parser.add_argument(
        '--port',
        default=80,
        type=int,
        help='Port to listen on. Default: [%(default)s]',
    )
    parser.add_argument(
        '--upstream-resolver',
        default='::1',
        help='Upstream recursive resolver to send the query to. '
             'Default: [%(default)s]',
    )
    parser.add_argument(
        '--uri',
        default=constants.DOH_URI,
        help='DNS API URI. Default [%(default)s]',
    )
    parser.add_argument(
        '--level',
        default='DEBUG',
        help='log level [%(default)s]',
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Debugging messages...'
    )
    return parser.parse_args()


async def doh1handler(request):
    path, params = utils.extract_path_params(request.rel_url.path_qs)

    if request.method == 'GET':
        if constants.DOH_CONTENT_TYPE_PARAM in params and \
                len(params[constants.DOH_CONTENT_TYPE_PARAM]):
            ct = params[constants.DOH_CONTENT_TYPE_PARAM][0]
        else:
            return aiohttp.web.Response(status=400, body=b'Missing Body')

        if constants.DOH_BODY_PARAM in params and \
                len(params[constants.DOH_BODY_PARAM]):
            body = utils.doh_b64_decode(
                params[constants.DOH_BODY_PARAM][0])
        else:
            return aiohttp.web.Response(status=400, body=b'Missing Body')

    else:
        body = request.content.read()
        ct = request.headers.get('content-type')

    if ct != constants.DOH_MEDIA_TYPE:
        return aiohttp.web.Response(
            status=415, body=b'Unsupported content type'
        )

    # Do actual DNS Query
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
    app = DOHApplication(logger=logger)
    app.set_upstream_resolver(args.upstream_resolver)
    app.router.add_get(args.uri, doh1handler)
    aiohttp.web.run_app(app, host=args.listen_address, port=args.port)


if __name__ == '__main__':
    main()
