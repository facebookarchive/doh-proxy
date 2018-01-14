#!/usr/bin/env python3
#
# Copyright (c) 2018-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
#
import argparse
import base64
import logging
import urllib.parse

from dohproxy import constants


def doh_b64_encode(s):
    """Base 64 urlsafe encode and remove padding.
    input: bytes
    output: str
    """
    return base64.urlsafe_b64encode(s).decode('utf-8').rstrip('=')


def doh_b64_decode(s):
    """Base 64 urlsafe decode, add padding as needed.
    input: str
    output: bytes
    """
    padding = '=' * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + padding)


def build_query_params(dns_query):
    """Given a wire-format DNS query, build the query parameters.
    """
    contenttype = constants.DOH_MEDIA_TYPE
    return {
        constants.DOH_BODY_PARAM: doh_b64_encode(dns_query),
        constants.DOH_CONTENT_TYPE_PARAM: contenttype,
    }


def make_url(domain, uri):
    """Utility function to return a URL ready to use from a browser or cURL....
    """
    p = urllib.parse.ParseResult(
        scheme='https',
        netloc=domain,
        path=uri,
        params='', query='', fragment='',
    )
    return urllib.parse.urlunparse(p)


def client_parser_base():
    """Build a ArgumentParser object with all the default arguments that are
    useful to both client and stub.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--domain',
        default='localhost',
        help='Domain to make DOH request against. Default: [%(default)s]'
    )
    parser.add_argument(
        '--uri',
        default=constants.DOH_URI,
        help='DNS API URI. Default [%(default)s]',
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
        '--level',
        default='DEBUG',
        help='log level [%(default)s]',
    )
    parser.add_argument(
        '--insecure',
        action='store_true',
        help=argparse.SUPPRESS,
    )
    return parser


def configure_logger(name='', level='DEBUG'):
    """
    :param name: (optional) name of the logger, default: ''.
    :param level: (optional) level of logging, default: DEBUG.
    :return: a logger instance.
    """
    logging.basicConfig(format='%(asctime)s: %(levelname)8s: %(message)s')
    logger = logging.getLogger(name)
    level_name = level.upper()
    level = getattr(logging, level_name, None)
    if not isinstance(level, int):
        raise Exception("Invalid log level name : %s" % level_name)
    logger.setLevel(level)
    return logger
