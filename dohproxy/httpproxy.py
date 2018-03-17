#!/usr/bin/env python3
#
# Copyright (c) 2018-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
#
import aiohttp.web
import aiohttp_remotes
import asyncio
import dns.message
import dns.rcode
import time

from argparse import ArgumentParser, Namespace

from dohproxy import constants, utils
from dohproxy.server_protocol import (
    DNSClientProtocol,
    DOHDNSException,
    DOHParamsException,
)


def parse_args(args=None):
    parser = utils.proxy_parser_base(port=80, secure=False)
    parser.add_argument(
        '--trusted',
        nargs='*',
        default=['::1', '127.0.0.1'],
        help='Trusted reverse proxy list separated by space %(default)s. \
            If you do not want to add a trusted trusted reverse proxy, \
            just specify this flag with empty parameters.',
    )
    return parser.parse_args(args=args)


async def doh1handler(request):
    path, params = utils.extract_path_params(request.rel_url.path_qs)

    if request.method == 'GET':
        try:
            ct, body = utils.extract_ct_body(params)
        except DOHParamsException as e:
            return aiohttp.web.Response(status=400, body=e.body())
    else:
        body = await request.content.read()
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

    clientip = request.transport.get_extra_info('peername')[0]
    request.app.logger.info(
        '[HTTPS] {} (Original IP: {}) {}'.format(
            clientip,
            request.remote,
            utils.dnsquery2log(dnsq)
        )
    )
    return await request.app.resolve(request, dnsq)


class DOHApplication(aiohttp.web.Application):

    def set_upstream_resolver(self, upstream_resolver, upstream_port):
        self.upstream_resolver = upstream_resolver
        self.upstream_port = upstream_port

    async def resolve(self, request, dnsq):
        self.time_stamp = time.time()
        qid = dnsq.id
        queue = asyncio.Queue(maxsize=1)
        await self.loop.create_datagram_endpoint(
                lambda: DNSClientProtocol(
                    dnsq, queue, request.remote, logger=self.logger
                ),
                remote_addr=(self.upstream_resolver, self.upstream_port))

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

        clientip = request.transport.get_extra_info('peername')[0]
        interval = int((time.time() - self.time_stamp) * 1000)
        self.logger.info(
            '[HTTPS] {} (Original IP: {}) {} {}ms'.format(
                clientip,
                request.remote,
                utils.dnsans2log(dnsr),
                interval
            )
        )
        body = dnsr.to_wire()

        return aiohttp.web.Response(
            status=200,
            body=body,
            content_type=constants.DOH_MEDIA_TYPE,
        )


def setup_ssl(options: Namespace):
    """ Setup the SSL Context """
    ssl_context = None

    # If SSL is wanted, both certfile and keyfile must
    # be passed
    if bool(options.certfile) ^ bool(options.keyfile):
        ArgumentParser.error('To use SSL both --certfile and --keyfile must be'
                             'passed')
    elif options.certfile and options.keyfile:
        ssl_context = utils.create_ssl_context(options)

    return ssl_context


def get_app(args):
    logger = utils.configure_logger('doh-httpproxy', args.level)
    app = DOHApplication(logger=logger, debug=args.debug)
    app.set_upstream_resolver(args.upstream_resolver, args.upstream_port)
    app.router.add_get(args.uri, doh1handler)
    app.router.add_post(args.uri, doh1handler)

    # Get trusted reverse proxies and format it for aiohttp_remotes setup
    if len(args.trusted) == 0:
        x_forwarded_handling = aiohttp_remotes.XForwardedRelaxed()
    else:
        x_forwarded_handling = \
            aiohttp_remotes.XForwardedStrict([args.trusted])

    asyncio.ensure_future(aiohttp_remotes.setup(
        app,
        x_forwarded_handling)
    )
    return app


def main():
    args = parse_args()
    app = get_app(args)

    ssl_context = setup_ssl(args)
    aiohttp.web.run_app(
        app, host=args.listen_address, port=args.port, ssl_context=ssl_context)


if __name__ == '__main__':
    main()
