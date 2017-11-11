#!/usr/bin/env python3
#
# Copyright (c) 2018-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
#
import base64


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
