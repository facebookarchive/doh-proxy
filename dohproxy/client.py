#!/usr/bin/env python3
#
# Copyright (c) 2018-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
#
import asyncio
import dns.message

from dohproxy import client_protocol, utils


class Client(client_protocol.StubServerProtocol):
    def on_answer(self, addr, msg):
        try:
            print(dns.message.from_wire(msg))
        except Exception:
            self.logger.exception(msg)


def parse_args():
    parser = utils.client_parser_base()
    parser.add_argument(
        '--qname',
        default='example.com',
        help='Name to query for. Default [%(default)s]',
    )
    parser.add_argument(
        '--qtype',
        default='AAAA',
        help='Type of query. Default [%(default)s]',
    )
    parser.add_argument(
        '--dnssec',
        action='store_true',
        help='Enable DNSSEC validation.'
    )
    return parser.parse_args()


def build_query(args):
    dnsq = dns.message.make_query(
        qname=args.qname,
        rdtype=args.qtype,
        want_dnssec=args.dnssec,
    )
    dnsq.id = 0
    return dnsq


def main_sync(args):
    logger = utils.configure_logger('doh-client', level=args.level)
    client = Client(args=args, logger=logger)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.make_request(None, build_query(args)))


def main():
    args = parse_args()
    main_sync(args)


if __name__ == '__main__':
    main()
