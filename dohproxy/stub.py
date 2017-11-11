#!/usr/bin/env python3
#
# Copyright (c) 2018-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
#
import aioh2
import argparse
import asyncio
import dns.message
import ssl
import urllib.parse

from dohproxy import constants, utils


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--domain',
        default='localhost',
        help='Domain to make DOH request against. Default: [%(default)s]'
    )
    parser.add_argument(
        '--remote-address',
        help='Remote address where the DOH proxy is running. '
             'Default: [%(default)s]',
    )
    parser.add_argument(
        '--port',
        default=443,
        help='Port to connect to. Default: [%(default)s]'
    )
    parser.add_argument(
        '--listen-port',
        default=53,
        help='The port the stub should listen on. Default: [%(default)s]'
    )
    parser.add_argument(
        '--listen-address',
        default=None,
        help='The address the stub should listen on. Default: [%(default)s]'
    )
    parser.add_argument(
        '--dnssec',
        action='store_true',
        help='Enable DNSSEC validation.'
    )
    parser.add_argument(
        '--post',
        action='store_true',
        help='Use HTTP POST instead of GET.'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Prints some debugging output',
    )
    parser.add_argument(
        '--uri',
        default=constants.DOH_URI,
        help='DNS API URI. Default [%(default)s]',
    )
    parser.add_argument(
        '--insecure',
        action='store_true',
        help=argparse.SUPPRESS,
    )
    return parser.parse_args()


def build_query_params(query):
    contenttype = constants.DOH_MEDIA_TYPE
    return {
        constants.DOH_BODY_PARAM: utils.doh_b64_encode(query),
        constants.DOH_CONTENT_TYPE_PARAM: contenttype,
    }


def make_url(domain, uri):
    p = urllib.parse.ParseResult(
        scheme='https',
        netloc=domain,
        path=uri,
        params='', query='', fragment='',
    )
    return urllib.parse.urlunparse(p)


async def make_request(proto, args, addr, dnsq):
    # Open client connection
    if args.insecure:
        sslctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        sslctx.options |= ssl.OP_NO_SSLv2
        sslctx.options |= ssl.OP_NO_SSLv3
        sslctx.options |= ssl.OP_NO_COMPRESSION
        sslctx.set_default_verify_paths()
    else:
        sslctx = ssl.create_default_context()

    sslctx.set_alpn_protocols(constants.DOH_H2_NPN_PROTOCOLS)
    sslctx.set_npn_protocols(constants.DOH_H2_NPN_PROTOCOLS)

    client = await aioh2.open_connection(args.remote_address, args.port,
                                         functional_timeout=0.1,
                                         ssl=sslctx,
                                         server_hostname=args.domain)

    rtt = await client.wait_functional()
    if rtt:
        print('Round-trip time: %.1fms' % (rtt * 1000))

    headers = {'Accept': constants.DOH_MEDIA_TYPE}
    path = args.uri
    qid = dnsq.id
    dnsq.id = 0
    body = b''

    headers = [
        (':authority', args.domain),
        (':method', args.post and 'POST' or 'GET'),
        (':scheme', 'h2'),
    ]
    if args.post:
        headers.append(('content-type', constants.DOH_MEDIA_TYPE))
        body = dnsq.to_wire()
    else:
        params = build_query_params(dnsq.to_wire())
        print(params)
        params_str = urllib.parse.urlencode(params)
        if args.debug:
            url = make_url(args.domain, args.uri)
            print('Sending {}?{}'.format(url, params_str))
        path = args.uri + '?' + params_str

    headers.insert(0, (':path', path))
    headers.extend([
        ('content-length', str(len(body))),
    ])
    # Start request with headers
    # import pdb; pdb.set_trace()
    stream_id = await client.start_request(headers, end_stream=not body)

    # Send my name "world" as whole request body
    if body:
        await client.send_data(stream_id, body, end_stream=True)

    # Receive response headers
    headers = await client.recv_response(stream_id)
    print('Response headers:', headers)

    # Read all response body
    resp = await client.read_stream(stream_id, -1)
    dnsr = dns.message.from_wire(resp)
    dnsr.id = qid
    proto.on_answer(addr, dnsr.to_wire())

    # Read response trailers
    trailers = await client.recv_trailers(stream_id)
    print('Response trailers:', trailers)
    client.close_connection()


class StubServerProtocol:

    def __init__(self, args):
        self.args = args

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        dnsq = dns.message.from_wire(data)

        asyncio.ensure_future(make_request(self, self.args, addr, dnsq))

    def on_answer(self, addr, dnsr):
        self.transport.sendto(dnsr, addr)


def main():
    args = parse_args()
    loop = asyncio.get_event_loop()
    print("Starting UDP server")
    # One protocol instance will be created to serve all client requests
    listen = loop.create_datagram_endpoint(
        lambda: StubServerProtocol(args),
        local_addr=(args.listen_address, args.listen_port))
    transport, protocol = loop.run_until_complete(listen)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    transport.close()
    loop.close()


if __name__ == '__main__':
    main()
