#!/usr/bin/env python3
#
# Copyright (c) 2018-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
#
import asyncio

from dohproxy import client_protocol, utils


def parse_args():
    parser = utils.client_parser_base()
    parser.add_argument(
        '--listen-port',
        default=53,
        help='The port the stub should listen on. Default: [%(default)s]'
    )
    parser.add_argument(
        '--listen-address',
        default='::1',
        help='The address the stub should listen on. Default: [%(default)s]'
    )

    return parser.parse_args()


def main():
    args = parse_args()
    logger = utils.configure_logger('doh-stub', args.level)
    loop = asyncio.get_event_loop()
    logger.info("Starting UDP server")
    # One protocol instance will be created to serve all client requests
    listen = loop.create_datagram_endpoint(
        lambda: client_protocol.StubServerProtocol(args, logger=logger),
        local_addr=(args.listen_address, args.listen_port))
    transport, proto = loop.run_until_complete(listen)
    loop.run_until_complete(proto.setup_client())

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    transport.close()
    loop.close()


if __name__ == '__main__':
    main()
