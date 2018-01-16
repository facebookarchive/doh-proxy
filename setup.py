#!/usr/bin/env python3
#
# Copyright (c) 2018-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
#
from setuptools import setup

from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='doh-proxy',
    version='0.0.1',
    description='A client and proxy implementation of '
                'https://tools.ietf.org/html/draft-ietf-doh-dns-over-https-02',
    long_description=long_description,
    url='https://github.com/facebookexperimental/doh-proxy',
    author='Manu Bretelle',
    author_email='chantra@fb.com',
    license="BSD",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: Name Service (DNS)',
        'Topic :: Internet :: WWW/HTTP :: HTTP Servers',
        'Topic :: Security :: Cryptography',
        'Topic :: Utilities',
    ],
    keywords='doh proxy dns https',
    packages=['dohproxy'],
    setup_requires=[
        'flake8',
        'pytest-runner',
    ],
    install_requires=[
        'aioh2 >= 0.2.1',
        'aiohttp',
        'dnspython',
    ],
    tests_require=[
        'pytest',
        'unittest-data-provider',
    ],
    entry_points={
        'console_scripts': [
            'doh-client = dohproxy.client:main',
            'doh-proxy = dohproxy.proxy:main',
            'doh-httpproxy = dohproxy.httpproxy:main',
            'doh-stub = dohproxy.stub:main',
        ],
    },
)
