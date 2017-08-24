from datetime import tzinfo, timedelta


class UTC(tzinfo):
    """tzinfo derived concrete class for UTC"""
    _offset = timedelta(0)
    _dst = timedelta(0)
    _name = "UTC"

    def utcoffset(self, dt):
        return self.__class__._offset

    def dst(self, dt):
        return self.__class__._dst

    def tzname(self, dt):
        return self.__class__._name


UTC = UTC()
