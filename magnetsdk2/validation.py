import datetime
import re
from collections import Iterable

import iso8601
import rfc3987
import six

_UUID_REGEX = re.compile(
    "(?i)^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def is_valid_uuid(value):
    """Validates if a value is a string representation of a UUID.
    :param value: string to validate
    :return: a boolean
    """
    return isinstance(value, six.string_types) and _UUID_REGEX.match(value)


def is_valid_uri(value):
    """Validates if a value is a valid string with an URI.
    :param value: string to validate
    :return: a boolean
    """
    return isinstance(value, six.string_types) and rfc3987.match(value, 'URI')


def is_valid_port(value):
    """Validates if a value is a valid integer with a TCP/UDP port number.
    :param value: string to validate
    :return: a boolean
    """
    return isinstance(value, six.integer_types) and 1 <= value <= 65535


def is_valid_alert_sortBy(value):
    """Validates if a value is a valid string with an alert sortBy parameter value as per the
    Magnet API v2 specification.
    :param value: string to validate
    :return: a boolean
    """
    return isinstance(value, six.string_types) and value in ('logDate', 'batchDate')


def is_valid_alert_status(value):
    """Validates if a value is a valid string with an alert status value as per the Magnet API v2
    specification.
    :param value: string to validate
    :return: a boolean
    """
    if not isinstance(value, Iterable):
        return False
    for string in value:
        if not isinstance(string, six.string_types) or string not in ('new', 'under_investigation',
                                                                      'rejected', 'resolved'):
            return False
    return True


def parse_date(value):
    """Extracts a datetime.date object from a string containing an ISO 8601 date, a
    datetime.datetime object or a datetime.date object.
    :param value: string to parse, datetime.date or datetime.datetime instance
    :return: a datetime.date instance
    """
    if isinstance(value, six.string_types):
        return iso8601.parse_date(value).date().isoformat()
    elif isinstance(value, datetime.datetime):
        return value.date().isoformat()
    elif isinstance(value, datetime.date):
        return value.isoformat()
    else:
        raise ValueError('date must be in ISO format: ' + repr(value))
