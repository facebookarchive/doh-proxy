#!/usr/bin/env python3
#
# Copyright (c) 2018-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
#
import argparse
import dns.message
import hyper
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
        '--port',
        default=443,
        help='Port to connect to. Default: [%(default)s]'
    )
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


def build_body(args):
    dnsq = dns.message.make_query(
        qname=args.qname,
        rdtype=args.qtype,
        want_dnssec=args.dnssec,
    )
    dnsq.id = 0
    return dnsq.to_wire()


def build_query_params(args):
    body = build_body(args)
    contenttype = constants.DOH_MEDIA_TYPE
    return {
        constants.DOH_BODY_PARAM: utils.doh_b64_encode(body),
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


def main_sync(args):
    connection = hyper.HTTP20Connection(
        args.domain, args.port,
        force_proto='h2', secure=not args.insecure
    )

    headers = {'Accept': constants.DOH_MEDIA_TYPE}

    if args.post:
        headers['content-type'] = constants.DOH_MEDIA_TYPE
        body = build_body(args)
        stream_id = connection.request(
            'POST', args.uri,
            body=body, headers=headers
        )
    else:
        params = build_query_params(args)
        params_str = urllib.parse.urlencode(params)
        if args.debug:
            url = make_url(args.domain, args.uri)
            print('Sending {}?{}'.format(url, params_str))
        stream_id = connection.request(
            'GET', args.uri + '?' + params_str,
            headers=headers
        )

    response = connection.get_response(stream_id)

    if args.debug:
        print('Server response status: {}'.format(response.status))
    if response.status == 200:
        print(dns.message.from_wire(response.read()))


if __name__ == '__main__':
    args = parse_args()
    main_sync(args)
