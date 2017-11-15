# -*- coding: utf-8 -*-
"""
This module implements writing CEF format events.
"""

from math import ceil, trunc

import six

from magnetsdk2.time import seconds_from_UTC_epoch


def escape_header_entry(x):
    """
    Escapes backslashes and pipes from a header entry.
    :param x: the string value to escape
    :return: escaped and trimmed UTF-8 encoded str / bytes
    """
    if not isinstance(x, six.string_types):
        x = x.__str__()
    return x.replace('\\', '\\\\').replace('|', '\\|').strip()


def header(device_vendor, device_product, device_version, signature_id, name, severity):
    """
    Builds a CEF version 0 header with the given fields
    :return: escaped and trimmed UTF-8 encoded str / bytes
    """
    if isinstance(severity, float):
        severity = trunc(severity)
    if isinstance(severity, six.integer_types):
        if severity < 0 or severity > 10:
            raise ValueError('severity must be between 0 and 10')
        severity = '{0:d}'.format(severity)
    return '|'.join(map(escape_header_entry,
                        ['CEF:0', device_vendor, device_product, device_version, signature_id, name,
                         severity, ''])).strip()


def escape_extension_value(x):
    """
    Escapes backslashes, pipes, equals signs and newlines from an extension entry value.
    :param x: the string value to escape
    :return: escaped and trimmed UTF-8 encoded str / bytes
    """
    if not isinstance(x, six.string_types):
        x = x.__str__()
    return x.replace('\\', '\\\\').replace('=', '\\=').replace('\n', '\\n').replace('\r',
                                                                                    '\\r').strip()


def extension(fields):
    """
    Builds a CEF version 0 extension with the given fields. Fields will be sorted by name.
    :param fields: dict containing fields to include
    :return: escaped and trimmed UTF-8 encoded str / bytes
    """
    fields = sorted([(k, v) for k, v in six.iteritems(fields) if v], key=lambda x: x[0])
    return ' '.join([e[0].strip() + '=' + escape_extension_value(e[1])
                     for e in fields]).strip()


def timestamp(ts):
    """
    Converts an ISO date and time in UTC into milliseconds from epoch as expected by CEF format.
    :param ts: string containing the date and time in ISO 8601 format
    :return: number of milliseconds since epoch
    """
    if not ts:
        return None
    if not ts.endswith('Z'):
        ts = ts + 'Z'
    return '{0:d}'.format(trunc(seconds_from_UTC_epoch(ts) * 1000))


def convert_alert(obj, alert, organization):
    """
    Converts a Niddel Magnet v2 API alert into an approximate CEF version 0 representation.
    :param obj: file-like object in binary mode to write to
    :param alert: dict containing a Niddel Magnet v2 API
    :return: an str / bytes object containing a CEF event
    """
    obj.write(header(device_vendor='Niddel', device_product='Magnet', device_version='1.0',
                     signature_id='infected_outbound',
                     name='Potentially Infected or Compromised Endpoint',
                     severity=max(ceil(alert['confidence'] / 10), 0)).encode('UTF-8'))

    ext = {
        'cs1': organization,
        'cs1Label': 'organizationId',
        'cs2': alert['batchDate'],
        'cs2Label': 'batchDate',
        'start': timestamp(alert['logDate'] + 'T' + alert['aggFirst']),
        'end': timestamp(alert['logDate'] + 'T' + alert['aggLast']),
        'externalId': alert['id'],
        'cfp1': alert['confidence'],
        'cfp1Label': 'confidence',
        'cnt': alert['aggCount'],
        'shost': alert.get('netSrcIpRdomain', None),
        'src': alert.get('netSrcIp', None),
        'dst': alert.get('netDstIp', None),
        'dhost': alert.get('netDstDomain', None),
        'dpt': alert.get('netDstPort', None),
        'proto': alert.get('netL4proto', None),
        'app': alert.get('netL7proto', alert.get('netApp', None)),
        'suid': alert.get('netSrcUser', None),
        'deviceCustomDate1': timestamp(alert.get('createdAt', None)),
        'deviceCustomDate1Label': 'createdAt',
        'deviceCustomDate2': timestamp(alert.get('updatedAt', None)),
        'deviceCustomDate2Label': 'updatedAt',
        'deviceDirection': 1,
        'dtz': 'GMT'
    }

    if 'netBlocked' in alert:
        if alert['netBlocked']:
            ext['act'] = 'allow'
        else:
            ext['act'] = 'deny'

    if 'tags' in alert:
        ext['cs3'] = ','.join(sorted(alert['tags']))
        ext['cs3Label'] = 'tags'

    if 'netDeviceTypes' in alert:
        ext['cs4'] = ','.join(sorted(alert['netDeviceTypes']))
        ext['cs4Label'] = 'netDeviceTypes'

    if 'netSrcProcessId' in alert:
        ext['cs5'] = alert['netSrcProcessId']
        ext['cs5Label'] = 'netSrcProcessId'

    # merge header and extension
    obj.write(extension(ext).encode('UTF-8'))

