r"""
About
=====
Custom extensions and helper functions for noweb files using Pweave and Pandoc.

.. moduleauthor:: Brandon T. Willard <brandonwillard@gmail.com>
"""
from __future__ import absolute_import

VERSION = (0, 0, 1)


def get_version():
    return '{}.{}.{}'.format(VERSION[0], VERSION[1], VERSION[2])
