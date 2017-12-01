# -*- coding: utf-8 -*-
"""
A simple client that allows idiomatic access to the Niddel Magnet v2 REST API
(https://api.niddel.com/v2). Uses the wonderful requests (http://docs.python-requests.org/)
package to perform the requests.
"""
__version__ = '1.5.1'

# set up package logger
import logging
logging.getLogger(__name__).addHandler(logging.NullHandler())

# import Connection class into namespace, but handle failure during setup if
# dependencies are not present yet
try:
    from magnetsdk2.connection import Connection
except ImportError:
    pass
