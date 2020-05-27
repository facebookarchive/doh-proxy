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


# CLIENT_STORE['client'] is shared by all handlers.
CLIENT_STORE = {'client': None}


def parse_args():
    parser = utils.client_parser_base()
    parser.add_argument(
        '--listen-port',
        default=53,
        help='The port the stub should listen on. Default: [%(default)s]'
    )
    parser.add_argument(
        '--listen-address',
        default=['::1'],
        nargs='+',
        help='A list of addresses the proxy should listen on. '
             '"all" for all detected interfaces and addresses (netifaces '
             'required). Default: [%(default)s]'
    )

    return parser.parse_args()


def main():
    args = parse_args()
    logger = utils.configure_logger('doh-stub', args.level)
    loop = asyncio.get_event_loop()

    if "all" in args.listen_address:
        listen_addresses = utils.get_system_addresses()
    else:
        listen_addresses = args.listen_address

    transports = []
    for address in listen_addresses:
        logger.info("Starting UDP server: {}".format(address))
        # One protocol instance will be created to serve all client requests
        # for this UDP listen address
        cls = client_protocol.StubServerProtocolUDP
        listen = loop.create_datagram_endpoint(
            lambda: cls(args, logger=logger, client_store=CLIENT_STORE),
            local_addr=(address, args.listen_port))
        transport, proto = loop.run_until_complete(listen)
        transports.append(transport)
        loop.run_until_complete(proto.get_client())

        logger.info("Starting TCP server: {}".format(address))
        cls = client_protocol.StubServerProtocolTCP
        listen_tcp = loop.create_server(
            lambda: cls(args, logger=logger, client_store=CLIENT_STORE),
            host=address, port=args.listen_port)
        server_tcp = loop.run_until_complete(listen_tcp)
        transports.append(server_tcp)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    for transport in transports:
        transport.close()
    loop.close()


if __name__ == '__main__':
    main()
