# -*- coding: utf-8 -*-
"""
A simple client that allows idiomatic access to the Niddel Magnet v2 REST API
(https://api.niddel.com/v2). Uses the wonderful requests (http://docs.python-requests.org/)
package to perform the requests.
"""

import logging

from magnetsdk2.connection import Connection

# set up package logger
logging.getLogger(__name__).addHandler(logging.NullHandler())
