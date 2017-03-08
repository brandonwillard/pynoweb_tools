r"""
About
=====
Custom extensions and helper functions for Pweave.

.. moduleauthor:: Brandon T. Willard <brandonwillard@gmail.com>
"""
from __future__ import absolute_import
from pweave_objs import *

VERSION = (0, 0, 1)


def get_version():
    return '{}.{}.{}'.format(VERSION[0], VERSION[1], VERSION[2])
