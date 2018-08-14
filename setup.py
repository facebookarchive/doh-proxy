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

import re

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


def read(*parts):
    with open(path.join(here, *parts), 'r') as fp:
        return fp.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r'^__version__ = [\'"]([^\'"]*)[\'"]',
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(
    name='doh-proxy',
    version=find_version('dohproxy', '__init__.py'),
    description='A client and proxy implementation of '
                'https://tools.ietf.org/html/draft-ietf-doh-dns-over-https-13',
    long_description=long_description,
    long_description_content_type='text/markdown',
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
    extras_require={
       'integration_tests': ['colour-runner'],
    },
    install_requires=[
        'aioh2 >= 0.2.1',
        'aiohttp >= 2.3.0',
        'dnspython',
        'aiohttp_remotes >= 0.1.2'
    ],
    tests_require=[
        'asynctest',
        'pytest',
        'pytest-aiohttp',
        'pytest-cov',
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
