# -*- coding: utf-8 -*-
"""
This module implements the Connection class, which is used for low-level interaction with the
Niddel Magnet v2 API.
"""

import logging
import os
import sys
import json

import six
from requests import request
from six.moves.configparser import RawConfigParser
from six.moves.urllib.parse import urlsplit, quote_plus

from magnetsdk2.time import UTC
from magnetsdk2.validation import is_valid_uuid, is_valid_uri, is_valid_port, \
    is_valid_alert_sortBy, is_valid_alert_status, parse_date

from magnetsdk2.connection import Connection

class ConnectionTest(Connection):
    
    def __init__(self, profile='default', api_key=None, endpoint=None):
        self.api_key = api_key
        self.endpoint = endpoint

    def iter_organizations(self):
        """ Test function simulating the case when the API key has acces only to the 
        Demo Organization.
        :return: an iterator over the decoded JSON objects that represent organizations.
        """
        """return json.dumps(
            {u'status': u'suspended', \
            u'name': u'Demo Organization', \
            u'roles': [u'admin'], \
            u'id': u'149ab4da-ab74-11e6-9671-0a7e67dda05f', \
            u'nickname': u'NiddelDemo', \
            u'properties': {u'bucketRegion': u'us-east-1', \
            u'bucketReportPrefix': u'reports', \
            u'bucket': u'niddel-149ab4da-ab74-11e6-9671-0a7e67dda05f', \
            u'maxWhitelists': 500, u'bucketUploadPrefix': u'upload', u'maxBlacklists': 500}})"""

        org_ids = os.listdir('./tests/data_test/')
        return [x.replace('.alerts.json', '') for x in org_ids]

    def get_organization(self, organization_id):
        """ Retrieves detailed data from an organization this API key has accessed to based on its
        ID.
        :param organization_id: string with the UUID-style unique ID of the organization
        :return: decoded JSON objects that represents the organization or None if not found
        """
        if not is_valid_uuid(organization_id):
            raise ValueError("organization id should be a string in UUID format")

        return json.dumps(
            {u'status': u'suspended', \
            u'name': u'Demo Organization', \
            u'roles': [u'admin'], \
            u'id': str(organization_id), \
            u'nickname': u'NiddelDemo', \
            u'properties': {u'bucketRegion': u'us-east-1', \
            u'bucketReportPrefix': u'reports', \
            u'bucket': u'niddel-' + str(organization_id), \
            u'maxWhitelists': 500, u'bucketUploadPrefix': u'upload', u'maxBlacklists': 500}})

    def iter_organization_alerts(self, organization_id, latest_alert_id, latest_batch_time, latest_api_cursor):
        
        if not is_valid_uuid(organization_id):
            raise ValueError("organization id should be a string in UUID format")

        with open('./tests/data_test/' + organization_id + '.alerts.json', 'r') as f:
            data = json.load(f)
            for alert in data['data']:
                yield alert
        
    def iter_organization_alerts_timeline(self, organization_id, alert_id=None):
        """ Generator that allows iteration over an organization's alerts, with optional filters.
        :param organization_id: string with the UUID-style unique ID of the organization
        :return: an iterator over the decoded JSON objects that represent alerts.
        """
        if not is_valid_uuid(organization_id):
            raise ValueError("organization id should be a string in UUID format")
        if alert_id:
            if not is_valid_uuid(alert_id):
                raise ValueError("alert id should be a string in UUID format")

        alert_list = []
        with open('./tests/data_test/' + organization_id + '.json', 'r') as f:
            for line in f:
                alert_list.append(json.loads(line.replace('\n', '')))

        if alert_id in [x['id'] for x in alert_list]:
            return

        if alert_list:
            for alert in alert_list:
                yield alert
        else:
            return

    def get_alert_stream_cursor(self, version=1, latest_alert_id=None, latest_batch_time=None):
        """ Function the calculate the API stream cursor based on the version, last seen
        alert ID and batch time."""
        b_cursor = bytearray()
        # append 1 byte for 'version'
        b_cursor.extend(to_bytes(n=version, length=1))
        # append 16 bytes for 'alert_id'
        if not isinstance(latest_alert_id, UUID):
            alert_id = UUID(latest_alert_id)
        b_cursor.extend(alert_id.bytes)
        # append 4 bytes for the 'latest_batch_time' seconds
        b_cursor.extend(to_bytes(n=to_SecondOfDay(latest_batch_time), length=4))

        return base64.urlsafe_b64encode(str(b_cursor))

    def iter_organization_alerts_stream(self, organization_id, latest_api_cursor=None, latest_batch_date=None):

        if not is_valid_uuid(organization_id):
            raise ValueError("organization id should be a string in UUID format")

        alert_list = []

        json_file = './tests/data_test/' + organization_id + '.alerts.json'
        
        with open(json_file, 'r') as f:
            for line in f:
                alert_list.append(json.loads(line.replace('\n', '')))

        if latest_api_cursor:
            alert_list_cursor = []
            for alert in alert_list:
                alert_list_cursor.append(self.get_alert_stream_cursor(latest_alert_id=alert['id'], 
                                        latest_batch_time=str(alert['batchDate'] +'T'+ alert['batchTime'])))
            alert_list = alert_list[alert_list_cursor.index(latest_api_cursor) + 1:]

        elif latest_batch_date:
            alert_list_ret =[]
            for alert in alert_list:
                if alert['batchDate'] > parse_date(latest_batch_date):
                    alert_list_ret.append(alert)
            alert_list = alert_list_ret

        if alert_list:
            for alert in alert_list:
                #with open('fname.alerts', 'a') as f:
                #    f.write(' '.join([alert['createdAt'], ';alert_id:', alert['id'], ';batchdate:', alert['batchDate'], ';batchtime:', alert['batchTime'], "\n"]))
                yield alert
        else:
            return

    def get_me(self):
        """Queries the API about the user that owns the API key in use.
        :return: a dict representing the user details
        """
        return json.dumps(
            {u'email': u'demo@niddel.com', \
            u'firstName': u'Demo', u'hasOldPassword': False, \
            u'id': u'fxXxXxXb-0000-0000-00x0-x0x00xXx00XX', u'lastName': u'Demo', \
            u'roles': [u'Demo']})

    def get_alert_stream_cursor(self, version=1, latest_alert_id=None, latest_batch_time=None):
        """ Function the calculate the API stream cursor based on the version, last seen
        alert ID and batch time."""
        b_cursor = bytearray()
        # append 1 byte for 'version'
        b_cursor.extend(to_bytes(n=version, length=1))
        # append 16 bytes for 'alert_id'
        if not isinstance(latest_alert_id, UUID):
            alert_id = UUID(latest_alert_id)
        b_cursor.extend(alert_id.bytes)
        # append 4 bytes for the 'latest_batch_time' seconds
        b_cursor.extend(to_bytes(n=to_SecondOfDay(latest_batch_time), length=4))

        return base64.urlsafe_b64encode(str(b_cursor))

    