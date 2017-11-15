import datetime

import six
import iso8601


class UTC(datetime.tzinfo):
    """tzinfo derived concrete class for UTC"""
    _offset = datetime.timedelta(0)
    _dst = datetime.timedelta(0)
    _name = "UTC"

    def utcoffset(self, dt):
        return self.__class__._offset

    def dst(self, dt):
        return self.__class__._dst

    def tzname(self, dt):
        return self.__class__._name


UTC = UTC()

UTC_EPOCH = datetime.datetime(1970, 1, 1, tzinfo=UTC)


def seconds_from_UTC_epoch(value):
    if isinstance(value, six.string_types):
        value = iso8601.parse_date(value)
    elif not isinstance(value, datetime.datetime):
        raise ValueError('timestamp expected')
    return (value - UTC_EPOCH).total_seconds()
