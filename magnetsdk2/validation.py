from re import compile
from collections import Iterable
import six
import rfc3987
import iso8601
import datetime

_UUID_REGEX = compile("(?i)^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def is_valid_uuid(value):
    return isinstance(value, six.string_types) and _UUID_REGEX.match(value)


def is_valid_uri(value):
    return isinstance(value, six.string_types) and rfc3987.match(value, 'URI')


def is_valid_port(value):
    return isinstance(value, six.integer_types) and 1 <= value <= 65535


def is_valid_alert_sortBy(value):
    return isinstance(value, six.string_types) and value in ('logDate', 'batchDate')


def is_valid_alert_status(value):
    if not isinstance(value, Iterable):
        return False
    for s in value:
        if not isinstance(s, six.string_types) or s not in ('new', 'under_investigation', 'rejected', 'resolved'):
            return False
    return True


def parse_date(value):
    if isinstance(value, six.string_types):
        return iso8601.parse_date(value).date().isoformat()
    elif isinstance(value, datetime.datetime):
        return value.date().isoformat()
    elif isinstance(value, datetime.date):
        return value.isoformat()
    else:
        raise ValueError('date must be in ISO format')
