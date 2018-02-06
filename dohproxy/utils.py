#!/usr/bin/env python3
#
# Copyright (c) 2018-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
#
import argparse
import binascii
import base64
import dns.exception
import dns.message
import logging
import urllib.parse

from typing import Dict, List, Tuple

from dohproxy import constants, protocol


def extract_path_params(url: str) -> Tuple[str, Dict[str, List[str]]]:
    """ Given a URI, extract the path and the parameters
    """
    p = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(p.query, keep_blank_values=True)
    return p.path, params


def extract_ct_body(params: Dict[str, List[str]]) -> Tuple[str, bytes]:
    """ Extract the content type and body from a list of get parameters.
    :param params: A dictionary of key/value of parameters as provided by
        urllib.parse.parse_qs
    :return: a tuple that contains a string and bytes, respectively ct and
        body.
    :raises: a DOHParamsException with an explanatory message.
    """
    if constants.DOH_CONTENT_TYPE_PARAM in params and \
            len(params[constants.DOH_CONTENT_TYPE_PARAM]):
        ct = params[constants.DOH_CONTENT_TYPE_PARAM][0]
        if not ct:
            # An empty value indicates the default
            # application/dns-udpwireformat type
            ct = constants.DOH_MEDIA_TYPE
    else:
        raise protocol.DOHParamsException(b'Missing Content Type Parameter')

    if constants.DOH_DNS_PARAM in params and \
            len(params[constants.DOH_DNS_PARAM]):
        try:
            body = doh_b64_decode(
                params[constants.DOH_DNS_PARAM][0])
        except binascii.Error:
            raise protocol.DOHParamsException(b'Invalid Body Parameter')
        if not body:
            raise protocol.DOHParamsException(b'Missing Body')
    else:
        raise protocol.DOHParamsException(b'Missing Body Parameter')

    return ct, body


def dns_query_from_body(
        body: bytes,
        debug: bool = False) -> dns.message.Message:
    """ Given a bytes-object, attempt to unpack a DNS Message.
    :param body: the bytes-object wired representation of a DNS message.
    :param debug: a boolean. When True, The error message sent to client will
    be more meaningful.
    :return: a dns.message.Message on success, raises DOHDNSException
    otherwise.
    """
    exc = b'Malformed DNS query'
    try:
        return dns.message.from_wire(body)
    except Exception as e:
        if debug:
            exc = str(e).encode('utf-8')
    raise protocol.DOHDNSException(exc)


def doh_b64_encode(s: bytes) -> str:
    """Base 64 urlsafe encode and remove padding.
    :param s: input bytes-like object to be encoded.
    :return: urlsafe base 64 encoded string.
    """
    return base64.urlsafe_b64encode(s).decode('utf-8').rstrip('=')


def doh_b64_decode(s: str) -> bytes:
    """Base 64 urlsafe decode, add padding as needed.
    :param s: input base64 encoded string with potentially missing padding.
    :return: decodes bytes
    """
    padding = '=' * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + padding)


def build_query_params(dns_query):
    """Given a wire-format DNS query, build the query parameters.
    """
    return {
        constants.DOH_DNS_PARAM: doh_b64_encode(dns_query),
        constants.DOH_CONTENT_TYPE_PARAM: constants.DOH_MEDIA_TYPE,
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
    :return: a ArgumentParser object with the common client side arguments set.
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
        help='Remote address where the DOH proxy is running. If None, '
        '--domain will be resolved to lookup and IP. Default: [%(default)s]',
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


def proxy_parser_base(*, port: int,
                      secure: bool = True) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--listen-address',
        default='::1',
        help='The address the proxy should listen on. Default: [%(default)s]'
    )
    parser.add_argument(
        '--port', '--listen-port',
        default=port,
        type=int,
        help='Port to listen on. Default: [%(default)s]',
    )
    if secure:
        parser.add_argument(
            '--certfile',
            help='SSL cert file.'
        )
        parser.add_argument(
            '--keyfile',
            help='SSL key file.'
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
