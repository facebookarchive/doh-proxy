#!/usr/bin/env python3
#
# Copyright (c) 2018-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
#

import unittest

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


class TestTypoChecker(unittest.TestCase):
    def test_client_base_parser(self):
        """ Basic test to check that there is no stupid typos.
        """
        utils.client_parser_base()

    def test_configure_logger(self):
        """ Basic test to check that there is no stupid typos.
        """
        utils.configure_logger()


def extract_path_params_source():
    return [
        ('/foo?a=b&c=d#1234', ('/foo', {'a': ['b'], 'c': ['d']})),
        ('/foo', ('/foo', {})),
        ('/foo?#', ('/foo', {})),
        ('foo', ('foo', {})),
    ]


class TestExtractPathParams(unittest.TestCase):
    @data_provider(extract_path_params_source)
    def test_make_url(self, uri, output):
        path, params = utils.extract_path_params(uri)
        self.assertEqual(path, output[0])
        self.assertDictEqual(params, output[1])
