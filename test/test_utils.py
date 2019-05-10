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
import dns.rcode
import ssl
import tempfile
import unittest
import argparse

from unittest.mock import patch, MagicMock

from dohproxy import constants
from dohproxy import server_protocol
from dohproxy import utils
from unittest_data_provider import data_provider

# Randomly generated source of words/b64
# gshuf /usr/share/dict/words | head -n 20 | while read line
# do
#    echo -e "(b'$line', '$(echo -n $line | base64 | tr -d '='  )',),"
# done

TEST_CA = ("-----BEGIN CERTIFICATE-----\n"
           "MIIDVzCCAj+gAwIBAgIJAOGYgypV1bcIMA0GCSqGSIb3DQEBCwUAMEIxCzAJBgNV\n"
           "BAYTAlhYMRUwEwYDVQQHDAxEZWZhdWx0IENpdHkxHDAaBgNVBAoME0RlZmF1bHQg\n"
           "Q29tcGFueSBMdGQwHhcNMTgwMjI2MjIxODA3WhcNMjgwMjI0MjIxODA3WjBCMQsw\n"
           "CQYDVQQGEwJYWDEVMBMGA1UEBwwMRGVmYXVsdCBDaXR5MRwwGgYDVQQKDBNEZWZh\n"
           "dWx0IENvbXBhbnkgTHRkMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA\n"
           "zkceT8GjMPz7e6nU30CO6aEonx3iszpNXpa+nH31M1NBs4wF2Rli9M1exyX2tAu9\n"
           "gr4ImpIXurryeT61RJYprRBLBdy2FBwx7tgSOeaxZupnQkfd7HwtBJD3dg7cBGpe\n"
           "RbJ44CQozLt0n16FM7yX2NwBxBxMKG+Brqo+PB9dR219Nzh5jB/UTWH21rrMYjiW\n"
           "ABa0OnMh/oc/YGSuR7ymtYWIKL2u3fZ1wV6yCblAKDIhAOhxY3yL6SxyS4uE2j8i\n"
           "XuMNCApD7mKbS3DGK6/H/zbn5jVwpzPr1FCPCkuWixoFH9Om6d7+x0HPrrO7yYND\n"
           "5cNxqR8mpsy2tpHDG+9MyQIDAQABo1AwTjAdBgNVHQ4EFgQUxLNYNYbSS7j6P6Wh\n"
           "UwToShMPcPIwHwYDVR0jBBgwFoAUxLNYNYbSS7j6P6WhUwToShMPcPIwDAYDVR0T\n"
           "BAUwAwEB/zANBgkqhkiG9w0BAQsFAAOCAQEACj/aXTKWStuM7PaiGzeuDHCyIRMm\n"
           "fDoRndTZXMH3bKmIb+2DlTjcLvHUeFSs21opssPL1U1fcvJRi3Yd5DYboiKILjO/\n"
           "0iNVGx6CPMiZZsYb+yeoA2ZtVqe/HoKzmeak4nP/QTv5xYRtFgSzXFmEPuC8CWdr\n"
           "xBdVAGX08H8vYlQk72YjKS/eJ6WbrijU0OnI3ZVlhMmlhwzW1cr/QmJSPoTsbS+a\n"
           "3c2aLV6NGplhmr2CuqqznDKT/QfxSk5qMoKAMdtA4iT5S5fPG5kGExt2MD+aimOw\n"
           "DOeHuyCLRXxIolT+8r2BY56sV1uYyuBFw0RAnEpmnc2d072DND6XcDeQCw==\n"
           "-----END CERTIFICATE-----")


def b64_source():
    return [
        (
            b'punner',
            'cHVubmVy',
        ),
        (
            b'visitation',
            'dmlzaXRhdGlvbg',
        ),
        (
            b'werf',
            'd2VyZg',
        ),
        (
            b'Hysterophyta',
            'SHlzdGVyb3BoeXRh',
        ),
        (
            b'diurne',
            'ZGl1cm5l',
        ),
        (
            b'reputableness',
            'cmVwdXRhYmxlbmVzcw',
        ),
        (
            b'uncompletely',
            'dW5jb21wbGV0ZWx5',
        ),
        (
            b'thalami',
            'dGhhbGFtaQ',
        ),
        (
            b'unpapal',
            'dW5wYXBhbA',
        ),
        (
            b'nonapposable',
            'bm9uYXBwb3NhYmxl',
        ),
        (
            b'synalgic',
            'c3luYWxnaWM',
        ),
        (
            b'exscutellate',
            'ZXhzY3V0ZWxsYXRl',
        ),
        (
            b'predelegation',
            'cHJlZGVsZWdhdGlvbg',
        ),
        (
            b'Varangi',
            'VmFyYW5naQ',
        ),
        (
            b'coucal',
            'Y291Y2Fs',
        ),
        (
            b'intensely',
            'aW50ZW5zZWx5',
        ),
        (
            b'apprize',
            'YXBwcml6ZQ',
        ),
        (
            b'jirble',
            'amlyYmxl',
        ),
        (
            b'imparalleled',
            'aW1wYXJhbGxlbGVk',
        ),
        (
            b'dinornithic',
            'ZGlub3JuaXRoaWM',
        ),
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
        (
            'foo',
            'uri',
            'https://foo/uri',
        ),
        (
            'foo',
            '/uri',
            'https://foo/uri',
        ),
        (
            'foo',
            '/uri/',
            'https://foo/uri/',
        ),
        (
            'foo:8443',
            '/uri/',
            'https://foo:8443/uri/',
        ),
    ]


class TestMakeURL(unittest.TestCase):
    @data_provider(make_url_source)
    def test_make_url(self, domain, uri, output):
        self.assertEqual(utils.make_url(domain, uri), output)


class TestBuildQueryParams(unittest.TestCase):
    def test_has_right_keys(self):
        """ Check that this function returns body only. """
        keys = {
            constants.DOH_DNS_PARAM,
        }
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
            utils.doh_b64_encode(q), params[constants.DOH_DNS_PARAM])


class TestTypoChecker(unittest.TestCase):
    def test_client_base_parser(self):
        """ Basic test to check that there is no stupid typos.
        """
        utils.client_parser_base()

    def test_proxy_base_parser_noargs(self):
        """ We must provide a port parameter to proxy_parser_base. """
        with self.assertRaises(TypeError):
            utils.proxy_parser_base()

    def test_proxy_base_default_secure_require_certs(self):
        """ If secure (default), will ask for the certfile and keyfile """
        p = utils.proxy_parser_base(port=80)
        # Since we are secure, we need --certfile and --keyfile
        with self.assertRaises(SystemExit) as e:
            args, left = p.parse_known_args()
        self.assertEqual(e.exception.code, 2)  # exit status must be 2

    def test_proxy_base_non_secure_no_certfile(self):
        """ If not using TLS, we don't suggest TLS related arguments. """
        p = utils.proxy_parser_base(port=80, secure=False)
        args, left = p.parse_known_args()
        # The values for cerfile and keyfile must be empty
        self.assertIsNone(args.certfile)
        self.assertIsNone(args.keyfile)

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
        ('/foo?a=b&c=d#1234', ('/foo', {
            'a': ['b'],
            'c': ['d']
        })),
        ('/foo', ('/foo', {})),
        ('/foo?#', ('/foo', {})),
        ('foo', ('foo', {})),
        # Test that we keep empty values
        ('/foo?a=b&c', ('/foo', {
            'a': ['b'],
            'c': ['']
        })),
        ('/foo?a=b&c=', ('/foo', {
            'a': ['b'],
            'c': ['']
        })),
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
            '/foo?ct&dns=aW1wYXJhbGxlbGVk',
            (constants.DOH_MEDIA_TYPE, b'imparalleled'),
        ),
        (
            '/foo?ct=&dns=aW1wYXJhbGxlbGVk',
            (constants.DOH_MEDIA_TYPE, b'imparalleled'),
        ),
        (
            '/foo?ct=bar&dns=aW1wYXJhbGxlbGVk',
            (constants.DOH_MEDIA_TYPE, b'imparalleled'),
        ),
        (
            '/foo?dns=aW1wYXJhbGxlbGVk',
            (constants.DOH_MEDIA_TYPE, b'imparalleled'),
        ),
    ]


def extract_ct_body_invalid_source():
    return [(
        '/foo?ct=&dns=',
        'Missing Body',
    ), (
        '/foo?ct=',
        'Missing Body Parameter',
    ), (
        '/foo?ct=bar&dns=_',
        'Invalid Body Parameter',
    )]


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
        with self.assertRaisesRegex(server_protocol.DOHParamsException,
                                    output):
            utils.extract_ct_body(params)


class TestDNSQueryFromBody(unittest.TestCase):
    def test_invalid_message_no_debug(self):
        body = 'a'
        with self.assertRaisesRegex(server_protocol.DOHDNSException,
                                    'Malformed DNS query'):
            utils.dns_query_from_body(body)

    def test_invalid_message_with_debug(self):
        body = 'a'
        with self.assertRaisesRegex(server_protocol.DOHDNSException,
                                    'is too short'):
            utils.dns_query_from_body(body, debug=True)

    def test_valid_message(self):
        dnsq = dns.message.Message()
        body = dnsq.to_wire()
        self.assertEqual(utils.dns_query_from_body(body), dnsq)


class TestDNSQuery2Log(unittest.TestCase):
    def setUp(self):
        self._qname = 'example.com'
        self._qtype = 'A'
        self._q = dns.message.make_query(self._qname, self._qtype)

    def test_valid_query(self):
        """
        test that no exception is thrown with a legitimate query.
        """
        utils.dnsquery2log(self._q)

    def test_valid_response(self):
        """
        test that no exception is thrown with a legitimate response.
        """
        r = dns.message.make_response(self._q, recursion_available=True)
        utils.dnsquery2log(r)

    def test_refused_response_no_question(self):
        """
        test that no exception is thrown with a legitimate response.
        """
        r = dns.message.make_response(self._q, recursion_available=True)
        r.set_rcode(dns.rcode.REFUSED)
        r.question = []
        utils.dnsquery2log(r)


class TestDNSAns2Log(unittest.TestCase):
    def setUp(self):
        self._qname = 'example.com'
        self._qtype = 'A'
        self._q = dns.message.make_query(self._qname, self._qtype)

    def test_valid_query(self):
        """
        test that no exception is thrown with a legitimate query.
        """
        utils.dnsans2log(self._q)

    def test_valid_response(self):
        """
        test that no exception is thrown with a legitimate response.
        """
        r = dns.message.make_response(self._q, recursion_available=True)
        utils.dnsans2log(r)

    def test_refused_response_no_question(self):
        """
        test that no exception is thrown with a legitimate response.
        """
        r = dns.message.make_response(self._q, recursion_available=True)
        r.set_rcode(dns.rcode.REFUSED)
        r.question = []
        utils.dnsans2log(r)


@patch('ssl.SSLContext.set_alpn_protocols', MagicMock())
@patch('ssl.SSLContext.load_cert_chain', MagicMock())
class TestProxySSLContext(unittest.TestCase):
    def setUp(self):
        self.args = argparse.Namespace()
        self.args.certfile = None
        self.args.keyfile = None

        # not all opnssl version may support DOH_CIPHERS, override with the one
        # supported by the testing platform
        constants.DOH_CIPHERS = ssl._DEFAULT_CIPHERS

    def test_proxy_ssl_context(self):
        """ Test a default ssl context, it should have http2 disabled """
        ssl_context = utils.create_ssl_context(self.args)
        self.assertIsInstance(ssl_context, ssl.SSLContext)
        # don't enable http2
        self.assertEqual(ssl_context.set_alpn_protocols.called, 0)

    def test_proxy_ssl_context_http2_enabled(self):
        """ Test a ssl context with http2 enabled """
        ssl_context = utils.create_ssl_context(self.args, http2=True)
        self.assertIsInstance(ssl_context, ssl.SSLContext)
        # enable http2
        self.assertEqual(ssl_context.set_alpn_protocols.called, 1)


class TestSSLContext(unittest.TestCase):
    def setUp(self):
        self._CA = TEST_CA
        self._CA_serial = "E198832A55D5B708"

        # ALPN requires >=openssl-1.0.2
        # NPN requires >=openssl-1.0.1
        for fn in ['set_alpn_protocols']:
            patcher = unittest.mock.patch('ssl.SSLContext.{0}'.format(fn))
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_insecure_context(self):
        """
        Test that insecure flag creates a context where verify method is
        CERT_NONE
        """
        sslctx = utils.create_custom_ssl_context(insecure=True)
        self.assertEqual(sslctx.verify_mode, ssl.CERT_NONE)

    def test_secure_context(self):
        """
        Test that if insecure is False, the ssl context created has
        CERT_REQUIRED as the verify method
        """
        sslctx = utils.create_custom_ssl_context(insecure=False)
        self.assertEqual(sslctx.verify_mode, ssl.CERT_REQUIRED)

    def test_cafile(self):
        with tempfile.NamedTemporaryFile() as ca:
            ca.write(self._CA.encode())
            ca.flush()
            sslctx = utils.create_custom_ssl_context(
                insecure=False, cafile=ca.name)
            self.assertTrue(
                self._CA_serial in
                [crt['serialNumber'] for crt in sslctx.get_ca_certs()])
