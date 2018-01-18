#!/usr/bin/env python3
#
# Copyright (c) 2018-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
#
import asyncio
import collections
import dns.message
import dns.rcode
import io
import ssl

from dohproxy import constants, utils
from dohproxy.protocol import (
    DNSClientProtocol,
    DOHDNSException,
    DOHParamsException,
)


from typing import List, Tuple

from h2.config import H2Configuration
from h2.connection import H2Connection
from h2.events import (
    ConnectionTerminated, DataReceived, RequestReceived, StreamEnded
)
from h2.errors import ErrorCodes
from h2.exceptions import ProtocolError


RequestData = collections.namedtuple('RequestData', ['headers', 'data'])


def parse_args():
    parser = utils.proxy_parser_base(port=443, secure=True)
    return parser.parse_args()


class H2Protocol(asyncio.Protocol):
    def __init__(self, upstream_resolver=None, uri=None, logger=None,
                 debug=False):
        config = H2Configuration(client_side=False, header_encoding='utf-8')
        self.conn = H2Connection(config=config)
        self.logger = logger
        if logger is None:
            self.logger = utils.configure_logger('doh-proxy', 'DEBUG')
        self.transport = None
        self.debug = debug
        self.stream_data = {}
        self.upstream_resolver = upstream_resolver
        self.uri = constants.DOH_URI if uri is None else uri
        assert upstream_resolver is not None, \
            'An upstream resolver must be provided'

    def connection_made(self, transport: asyncio.Transport):  # type: ignore
        self.transport = transport
        self.conn.initiate_connection()
        self.transport.write(self.conn.data_to_send())

    def data_received(self, data: bytes):
        try:
            events = self.conn.receive_data(data)
        except ProtocolError as e:
            self.transport.write(self.conn.data_to_send())
            self.transport.close()
        else:
            self.transport.write(self.conn.data_to_send())
            for event in events:
                if isinstance(event, RequestReceived):
                    self.request_received(event.headers, event.stream_id)
                elif isinstance(event, DataReceived):
                    self.receive_data(event.data, event.stream_id)
                elif isinstance(event, StreamEnded):
                    self.stream_complete(event.stream_id)
                elif isinstance(event, ConnectionTerminated):
                    self.transport.close()

                self.transport.write(self.conn.data_to_send())

    def request_received(self, headers: List[Tuple[str, str]], stream_id: int):
        _headers = collections.OrderedDict(headers)
        method = _headers[':method']
        # We only support GET and POST.
        if method not in ('GET', 'POST'):
            self.return_405(stream_id)
            return

        # Store off the request data.
        request_data = RequestData(_headers, io.BytesIO())
        self.stream_data[stream_id] = request_data

    def stream_complete(self, stream_id: int):
        """
        When a stream is complete, we can send our response.
        """
        try:
            request_data = self.stream_data[stream_id]
        except KeyError:
            # Just return, we probably 405'd this already
            return

        headers = request_data.headers
        method = request_data.headers[':method']

        # Handle the actual query
        path, params = utils.extract_path_params(headers[':path'])

        if path != self.uri:
            self.return_404(stream_id)
            return

        if method == 'GET':
            try:
                ct, body = utils.extract_ct_body(params)
            except DOHParamsException as e:
                self.return_400(stream_id, body=e.body())
                return
        else:
            body = request_data.data.getvalue()
            ct = headers.get('content-type')

        if ct != constants.DOH_MEDIA_TYPE:
            self.return_415(stream_id)
            return

        # Do actual DNS Query
        try:
            dnsq = utils.dns_query_from_body(body, self.debug)
        except DOHDNSException as e:
            self.return_400(stream_id, body=e.body())
            return

        self.logger.info(
            '[HTTPS] Received: ID {} Question {} Peer {}'.format(
                dnsq.id,
                dnsq.question[0],
                self.transport.get_extra_info('peername'),
            )
        )
        asyncio.ensure_future(self.resolve(dnsq, stream_id))

    def on_answer(self, stream_id, dnsr=None, dnsq=None):
        headers = {
            'Content-Type': constants.DOH_MEDIA_TYPE,
        }
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
                self.transport.get_extra_info('peername')
            )
        )
        body = dnsr.to_wire()

        response_headers = (
            (':status', '200'),
            ('content-type', constants.DOH_MEDIA_TYPE),
            ('content-length', str(len(body))),
            ('server', 'asyncio-h2'),
        )
        self.conn.send_headers(stream_id, response_headers)
        self.conn.send_data(stream_id, body, end_stream=True)
        self.transport.write(self.conn.data_to_send())

    async def resolve(self, dnsq, stream_id):
        qid = dnsq.id
        loop = asyncio.get_event_loop()
        queue = asyncio.Queue(maxsize=1)
        await loop.create_datagram_endpoint(
                lambda: DNSClientProtocol(dnsq, queue),
                remote_addr=(self.upstream_resolver, 53))

        self.logger.debug("Waiting for DNS response")
        try:
            dnsr = await asyncio.wait_for(queue.get(), 10)
            dnsr.id = qid
            queue.task_done()
            self.on_answer(stream_id, dnsr=dnsr)
        except asyncio.TimeoutError:
            self.logger.debug("Request timed out")
            self.on_answer(stream_id, dnsq=dnsq)

    def return_XXX(self, stream_id: int, status: int, body: bytes = b''):
        """
        Wrapper to return a status code and some optional content.
        """
        response_headers = (
            (':status', str(status)),
            ('content-length', str(len(body))),
            ('server', 'asyncio-h2'),
        )
        self.conn.send_headers(stream_id, response_headers)
        self.conn.send_data(stream_id, body, end_stream=True)

    def return_400(self, stream_id: int, body: bytes = b''):
        """
        We don't support the given PATH, so we want to return a 403 response.
        """
        self.return_XXX(stream_id, 400, body)

    def return_403(self, stream_id: int, body: bytes = b''):
        """
        We don't support the given PATH, so we want to return a 403 response.
        """
        self.return_XXX(stream_id, 403, body)

    def return_404(self, stream_id: int):
        """
        We don't support the given PATH, so we want to return a 403 response.
        """
        self.return_XXX(stream_id, 404, body=b'Wrong path')

    def return_405(self, stream_id: int):
        """
        We don't support the given method, so we want to return a 405 response.
        """
        self.return_XXX(stream_id, 405)

    def return_415(self, stream_id: int):
        """
        We don't support the given media, so we want to return a 415 response.
        """
        self.return_XXX(stream_id, 415, body=b'Unsupported content type')

    def receive_data(self, data: bytes, stream_id: int):
        """
        We've received some data on a stream. If that stream is one we're
        expecting data on, save it off. Otherwise, reset the stream.
        """
        try:
            stream_data = self.stream_data[stream_id]
        except KeyError:
            self.conn.reset_stream(
                stream_id, error_code=ErrorCodes.PROTOCOL_ERROR
            )
        else:
            stream_data.data.write(data)


def ssl_context(options):
    ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ctx.load_cert_chain(options.certfile, keyfile=options.keyfile)
    ctx.set_alpn_protocols(["h2"])
    ctx.options |= (
        ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_COMPRESSION
    )
    ctx.set_ciphers("ECDHE+AESGCM")

    return ctx


def main():
    args = parse_args()
    logger = utils.configure_logger('doh-proxy', args.level)
    ssl_ctx = ssl_context(args)
    loop = asyncio.get_event_loop()
    coro = loop.create_server(
        lambda: H2Protocol(
            upstream_resolver=args.upstream_resolver,
            uri=args.uri,
            logger=logger,
            debug=args.debug),
        host=args.listen_address,
        port=args.port,
        ssl=ssl_ctx)
    server = loop.run_until_complete(coro)

    # Serve requests until Ctrl+C is pressed
    logger.info('Serving on {}'.format(server))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()


if __name__ == '__main__':
    main()
