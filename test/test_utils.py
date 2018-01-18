#!/usr/bin/env python3
#
# Copyright (c) 2018-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
#

import binascii
import dns.message
import unittest

from dohproxy import constants
from dohproxy import protocol
from dohproxy import utils
from unittest_data_provider import data_provider

# Randomly generated source of words/b64
# gshuf /usr/share/dict/words | head -n 20 | while read line
# do
#    echo -e "(b'$line', '$(echo -n $line | base64 | tr -d '='  )',),"
# done


def b64_source():
    return [
        (b'punner', 'cHVubmVy',),
        (b'visitation', 'dmlzaXRhdGlvbg',),
        (b'werf', 'd2VyZg',),
        (b'Hysterophyta', 'SHlzdGVyb3BoeXRh',),
        (b'diurne', 'ZGl1cm5l',),
        (b'reputableness', 'cmVwdXRhYmxlbmVzcw',),
        (b'uncompletely', 'dW5jb21wbGV0ZWx5',),
        (b'thalami', 'dGhhbGFtaQ',),
        (b'unpapal', 'dW5wYXBhbA',),
        (b'nonapposable', 'bm9uYXBwb3NhYmxl',),
        (b'synalgic', 'c3luYWxnaWM',),
        (b'exscutellate', 'ZXhzY3V0ZWxsYXRl',),
        (b'predelegation', 'cHJlZGVsZWdhdGlvbg',),
        (b'Varangi', 'VmFyYW5naQ',),
        (b'coucal', 'Y291Y2Fs',),
        (b'intensely', 'aW50ZW5zZWx5',),
        (b'apprize', 'YXBwcml6ZQ',),
        (b'jirble', 'amlyYmxl',),
        (b'imparalleled', 'aW1wYXJhbGxlbGVk',),
        (b'dinornithic', 'ZGlub3JuaXRoaWM',),
    ]


class TestDOHB64(unittest.TestCase):
    @data_provider(b64_source)
    def test_b64_encode(self, input, output):
        self.assertEqual(utils.doh_b64_encode(input), output)

    @data_provider(b64_source)
    def test_b64_decode(self, output, input):
        self.assertEqual(utils.doh_b64_decode(input), output)

    def test_b64_decode_invalid(self):
        """ When providing an invalid input to base64.urlsafe_b64decode it
        should raise a binascii.Error exception.
        """
        with self.assertRaisesRegex(binascii.Error, 'Incorrect padding'):
            utils.doh_b64_decode('_')


def make_url_source():
    return [
        ('foo', 'uri', 'https://foo/uri',),
        ('foo', '/uri', 'https://foo/uri',),
        ('foo', '/uri/', 'https://foo/uri/',),
        ('foo:8443', '/uri/', 'https://foo:8443/uri/',),
    ]


class TestMakeURL(unittest.TestCase):
    @data_provider(make_url_source)
    def test_make_url(self, domain, uri, output):
        self.assertEqual(utils.make_url(domain, uri), output)


class TestBuildQueryParams(unittest.TestCase):

    def test_has_right_keys(self):
        """ Check that this function returns body and ct parameters only. """
        keys = set(
            [constants.DOH_BODY_PARAM, constants.DOH_CONTENT_TYPE_PARAM]
        )
        self.assertEqual(keys, utils.build_query_params(b'').keys())

    def test_query_must_be_bytes(self):
        """ Check that this function raises when we pass a string. """
        with self.assertRaises(TypeError):
            utils.build_query_params('')

    def test_query_accepts_bytes(self):
        """ Check that this function accepts a bytes-object. """
        utils.build_query_params(b'')

    def test_body_b64encoded(self):
        """ Check that this function is b64 encoding the content of body. """
        q = b''
        params = utils.build_query_params(q)
        self.assertEqual(
            utils.doh_b64_encode(q),
            params[constants.DOH_BODY_PARAM]
        )


class TestTypoChecker(unittest.TestCase):
    def test_client_base_parser(self):
        """ Basic test to check that there is no stupid typos.
        """
        utils.client_parser_base()

    def test_proxy_base_parser_noargs(self):
        """ We must provide a port parameter to proxy_parser_base. """
        with self.assertRaises(TypeError):
            utils.proxy_parser_base()

    def test_proxy_base_default_secure(self):
        """ If we don't specify `secure`, it will default to secure. """
        p = utils.proxy_parser_base(port=80)
        args, left = p.parse_known_args()
        # This would raise if certfile is not in Namespace
        args.certfile

    def test_proxy_base_non_secure_no_certfile(self):
        """ If not using TLS, we don't suggest TLS related arguments. """
        p = utils.proxy_parser_base(port=80, secure=False)
        args, left = p.parse_known_args()
        # This would raise if certfile is not in Namespace
        with self.assertRaises(AttributeError):
            args.certfile

    def test_configure_logger(self):
        """ Basic test to check that there is no stupid typos.
        """
        utils.configure_logger()

    def test_configure_logger_unknown_level(self):
        """ Basic test to check that there is no stupid typos.
        """
        with self.assertRaises(Exception):
            utils.configure_logger(level='thisisnotalevel')


def extract_path_params_source():
    return [
        ('/foo?a=b&c=d#1234', ('/foo', {'a': ['b'], 'c': ['d']})),
        ('/foo', ('/foo', {})),
        ('/foo?#', ('/foo', {})),
        ('foo', ('foo', {})),
        # Test that we keep empty values
        ('/foo?a=b&c', ('/foo', {'a': ['b'], 'c': ['']})),
        ('/foo?a=b&c=', ('/foo', {'a': ['b'], 'c': ['']})),
    ]


class TestExtractPathParams(unittest.TestCase):
    @data_provider(extract_path_params_source)
    def test_extract_path_params(self, uri, output):
        path, params = utils.extract_path_params(uri)
        self.assertEqual(path, output[0])
        self.assertDictEqual(params, output[1])


def extract_ct_body_valid_source():
    return [
        (
            '/foo?ct&body=aW1wYXJhbGxlbGVk',
            (constants.DOH_MEDIA_TYPE, b'imparalleled'),
        ),
        (
            '/foo?ct=&body=aW1wYXJhbGxlbGVk',
            (constants.DOH_MEDIA_TYPE, b'imparalleled'),
        ),
        (
            '/foo?ct=bar&body=aW1wYXJhbGxlbGVk',
            ('bar', b'imparalleled'),
        )
    ]


def extract_ct_body_invalid_source():
    return [
        (
            '/foo?body=aW1wYXJhbGxlbGVk',
            'Missing Content Type Parameter',
        ),
        (
            '/foo?ct=&body=',
            'Missing Body',
        ),
        (
            '/foo?ct=',
            'Missing Body Parameter',
        ),
        (
            '/foo?ct=bar&body=_',
            'Invalid Body Parameter',
        )
    ]


class TestExtractCtBody(unittest.TestCase):
    @data_provider(extract_ct_body_valid_source)
    def test_extract_ct_body_valid(self, uri, output):
        path, params = utils.extract_path_params(uri)
        ct, body = utils.extract_ct_body(params)
        self.assertEqual(ct, output[0])
        self.assertEqual(body, output[1])

    @data_provider(extract_ct_body_invalid_source)
    def test_extract_ct_body_invalid(self, uri, output):
        path, params = utils.extract_path_params(uri)
        with self.assertRaisesRegex(protocol.DOHParamsException, output):
            utils.extract_ct_body(params)


class TestDNSQueryFromBody(unittest.TestCase):
    def test_invalid_message_no_debug(self):
        body = 'a'
        with self.assertRaisesRegex(
                protocol.DOHDNSException, 'Malformed DNS query'):
            utils.dns_query_from_body(body)

    def test_invalid_message_with_debug(self):
        body = 'a'
        with self.assertRaisesRegex(
                protocol.DOHDNSException, 'is too short'):
            utils.dns_query_from_body(body, debug=True)

    def test_valid_message(self):
        dnsq = dns.message.Message()
        body = dnsq.to_wire()
        self.assertEqual(utils.dns_query_from_body(body), dnsq)
