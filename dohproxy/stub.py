#!/usr/bin/env python3
#
# Copyright (c) 2018-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
#
import aioh2
import asyncio
import dns.message
import ssl
import urllib.parse

from dohproxy import constants, utils


def parse_args():
    parser = utils.client_parser_base()
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
        '--remote-address',
        help='Remote address where the DOH proxy is running. '
             'Default: [%(default)s]',
    )

    return parser.parse_args()


class StubServerProtocol:

    def __init__(self, args):
        self.args = args

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        dnsq = dns.message.from_wire(data)

        asyncio.ensure_future(self.make_request(addr, dnsq))

    def on_answer(self, addr, dnsr):
        self.transport.sendto(dnsr, addr)

    async def make_request(self, addr, dnsq):
        # Open client connection
        if self.args.insecure:
            sslctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            sslctx.options |= ssl.OP_NO_SSLv2
            sslctx.options |= ssl.OP_NO_SSLv3
            sslctx.options |= ssl.OP_NO_COMPRESSION
            sslctx.set_default_verify_paths()
        else:
            sslctx = ssl.create_default_context()

        sslctx.set_alpn_protocols(constants.DOH_H2_NPN_PROTOCOLS)
        sslctx.set_npn_protocols(constants.DOH_H2_NPN_PROTOCOLS)

        client = await aioh2.open_connection(self.args.remote_address,
                                             self.args.port,
                                             functional_timeout=0.1,
                                             ssl=sslctx,
                                             server_hostname=self.args.domain)

        rtt = await client.wait_functional()
        if rtt:
            print('Round-trip time: %.1fms' % (rtt * 1000))

        headers = {'Accept': constants.DOH_MEDIA_TYPE}
        path = self.args.uri
        qid = dnsq.id
        dnsq.id = 0
        body = b''

        headers = [
            (':authority', self.args.domain),
            (':method', self.args.post and 'POST' or 'GET'),
            (':scheme', 'h2'),
        ]
        if self.args.post:
            headers.append(('content-type', constants.DOH_MEDIA_TYPE))
            body = dnsq.to_wire()
        else:
            params = utils.build_query_params(dnsq.to_wire())
            print(params)
            params_str = urllib.parse.urlencode(params)
            if self.args.debug:
                url = utils.make_url(self.args.domain, self.args.uri)
                print('Sending {}?{}'.format(url, params_str))
            path = self.args.uri + '?' + params_str

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
        self.on_answer(addr, dnsr.to_wire())

        # Read response trailers
        trailers = await client.recv_trailers(stream_id)
        print('Response trailers:', trailers)
        client.close_connection()


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
