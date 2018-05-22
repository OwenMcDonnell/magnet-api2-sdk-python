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
        return [x.replace('.json', '') for x in org_ids]

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

    def iter_organization_alerts(self, organization_id, fromDate=None, toDate=None,
                                 sortBy="logDate", status=None):
        """ Generator that allows iteration over an organization's alerts, with optional filters.
        :param organization_id: string with the UUID-style unique ID of the organization
        :param fromDate: only list alerts with dates >= this parameter
        :param toDate: only list alerts with dates <= this parameter
        :param sortBy: one of 'logDate' or 'batchDate', controls which date field fromDate and
        toDate apply to
        :param status: a list or set containing one or more of 'new', 'under_investigation',
        'rejected', 'resolved'
        :return: an iterator over the decoded JSON objects that represent alerts.
        """
        if not is_valid_uuid(organization_id):
            raise ValueError("organization id should be a string in UUID format")

        with open('./tests/data_test/' + organization_id + '.json', 'r') as f:
            for line in f:
                yield json.loads(line.replace('\n', ''))
        
    def iter_organization_alerts_timeline(self, organization_id, alert_id=None):
        """ Generator that allows iteration over an organization's alerts, with optional filters.
        :param organization_id: string with the UUID-style unique ID of the organization
        :return: an iterator over the decoded JSON objects that represent alerts.
        """
        if not is_valid_uuid(organization_id):
            raise ValueError("organization id should be a string in UUID format")
        if not is_valid_uuid(alert_id):
            raise ValueError("alert id should be a string in UUID format")

        alert_list = []
        with open('./tests/data_test/' + organization_id + '.json', 'r') as f:
            for line in f:
                alert_list.append(json.loads(line.replace('\n', '')))

        if alert_list:
            for alert in alert_list:
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
