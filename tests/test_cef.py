from magnetsdk2.cef import escape_header_entry, header, escape_extension_value, extension, \
    timestamp


def test_escape_header_entry():
    assert escape_header_entry("blah") == "blah"
    assert escape_header_entry("hello world") == "hello world"
    assert escape_header_entry("a|b") == "a\\|b"
    assert escape_header_entry("a\\b") == "a\\\\b"
    assert escape_header_entry("a\\b|c") == "a\\\\b\\|c"


def test_header():
    assert header('security', 'threatmanager', '1.0', '100', 'Detected a threat.', '10') == \
           "CEF:0|security|threatmanager|1.0|100|Detected a threat.|10|"
    assert header('security|piped', 'threat\\manager', '1.0', '100', 'Detected a threat.', '10') == \
           "CEF:0|security\\|piped|threat\\\\manager|1.0|100|Detected a threat.|10|"


def test_escape_extension_value():
    assert escape_extension_value("blah") == "blah"
    assert escape_extension_value("hello world") == "hello world"
    assert escape_extension_value("a|b") == "a|b"
    assert escape_extension_value("a\\b") == "a\\\\b"
    assert escape_extension_value("a=b") == "a\\=b"
    assert escape_extension_value("a\nb\rc") == "a\\nb\\rc"


def test_extension():
    assert extension({'src': '10.0.0.1', 'msg': 'Detected a threat.\n No action needed.'}) == \
           "msg=Detected a threat.\\n No action needed. src=10.0.0.1"


def test_timestamp():
    assert timestamp("1970-01-01T00:00:00Z") == '0'
    assert timestamp("2017-11-15T11:00:00Z") == '1510743600000'
