import logging
import sys
import os
import requests
import iso8601
import datetime
from pytz import UTC
from six.moves.urllib.parse import urlsplit
from six.moves.configparser import RawConfigParser

from validation import *

# Default values used for the configuration
_CONFIG_DIR = os.path.expanduser('~/.magnetsdk')
_CONFIG_FILE = os.path.join(_CONFIG_DIR, "config")
_DEFAULT_CONFIG = {'endpoint': 'https://api.niddel.com/api/v2'}
_API_KEY_HEADER = 'X-Api-Key'
_PAGE_SIZE = 100


class Connection(object):
    """ This class encapsulates accessing the Niddel Magnet v2 API (https://api.niddel.com/v2) using a particular
    configuration profile from ~/.magnetsdk/config, and is wrapper around a requests.Session instance that is used
    for all accesses.
    """

    def __init__(self, profile='default', api_key=None, endpoint=None):
        """ Initializes the connection with the proper configuration data. The underlying requests.Session object
        is created lazily when the first actual operation is executed.
        :param profile: the profile name to use in ~/.magnetsdk/config
        :param api_key: if provided, this API key is used instead of the one on the configuration file
        :param endpoint: if provided this endpoint URL is used instead of the one on the configuration file
        """
        # initialize logger and credential cache
        self._logger = logging.getLogger('magnetsdk2')
        self._org_creds_cache = {}

        # initially get configuration from environment
        self.endpoint = os.getenv('MAGNETSDK_API_ENDPOINT', _DEFAULT_CONFIG['endpoint'])
        self.api_key = os.getenv('MAGNETSDK_API_KEY')

        # read from configuration file and profile
        if profile and os.path.isfile(_CONFIG_FILE):
            parser = RawConfigParser(_DEFAULT_CONFIG)
            parser.read(_CONFIG_FILE)
            if not parser.has_section(profile):
                raise ValueError('profile %s not found in %s' % (profile, _CONFIG_FILE))
            self.api_key = parser.get(profile, 'api_key')
            self.endpoint = parser.get(profile, 'endpoint')

        # explicit parameters override whatever was read previously
        if api_key is not None:
            if not isinstance(api_key, six.string_types):
                raise ValueError("API key must be a string")
            self.api_key = api_key
        if endpoint is not None:
            if not is_valid_uri(endpoint):
                raise ValueError("endpoint must be a string containing a valid URL")
            self.endpoint = endpoint

        # ensure we have an API key to work with
        if not self.api_key:
            raise ValueError('no API key to use')

        # parse endpoint data and ensure it ends with a slash
        endpoint = urlsplit(self.endpoint, 'https')
        self.endpoint = endpoint.geturl()
        if not self.endpoint.endswith('/'):
            self.endpoint += '/'

        # check for certificate pinning for the destination server
        if os.path.isfile(os.path.join(_CONFIG_DIR, endpoint.hostname + '.pem')):
            self.verify = os.path.join(_CONFIG_DIR, endpoint.hostname + '.pem')
        else:
            self.verify = True

        self._logger.debug('%s: endpoint=%r, verify=%r' % (self.__class__.__name__, self.endpoint, self.verify))
        self._session = None

    def __del__(self):
        self.close()

    def close(self):
        """ Closes the internal request.Session object and clears the credential cache.
        """
        if self._session:
            self._session.close()
            self._session = None
        if self._org_creds_cache:
            self._org_creds_cache.clear()

    def _request(self, method, path, params=None, body=None):
        """ Performs an HTTP operation using the base API endpoint, API key and SSL validation / cert pinning obtained
        from the configuration file. Creates a new session object if necessary.
        :param method: string with the the HTTP method to use ('GET', 'PUT', etc.)
        :param path: string with the path to append to the base API endpoint
        :param params: dict with the query parameters to submit
        :return: the requests.Response object
        """
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({_API_KEY_HEADER: self.api_key, "Accept-Encoding": "gzip, deflate",
                                          "User-Agent": "magnet-sdk-python", "Accept": "application/json"})
            self._session.verify = self.verify

        req = requests.Request(method=method, url=self.endpoint + path, params=params, json=body)
        req = self._session.prepare_request(req)
        if req.body:
            self._logger.debug('{0:s} {1:s} ({2:d} bytes in body)'.format(req.method, req.url, len(req.body)))
        else:
            self._logger.debug('{0:s} {1:s}'.format(req.method, req.url))
        return self._session.send(req)

    def _request_retry(self, method, path, params=None, body=None, ok_status=(200, 404), retries=5):
        """ Wrapper around self._request that retries on exceptions and unexpected status codes.
        """
        i = 1
        while True:
            try:
                response = self._request(method, path, params, body)
                if i >= retries or response.status_code in ok_status:
                    return response
            except:
                self._logger.exception(
                    'error at try %i of %s request for %s with params=%s' % (i, method, path, repr(params)))
                if i >= retries:
                    six.reraise(*sys.exc_info())
            i += 1

    def iter_organizations(self):
        """ Generator that allows iteration over all of the organizations that this connections's API key
        has access to.
        :return: an iterator over the decoded JSON objects that represent organizations.
        """
        params = {
            'page': 1,
            'size': _PAGE_SIZE
        }
        while True:
            response = self._request_retry("GET", path='organizations', params=params)
            if response.status_code == 200:
                orgs = response.json()
                for o in orgs:
                    yield o
                if len(orgs) < _PAGE_SIZE:
                    return
            elif response.status_code == 404:
                return
            else:
                response.raise_for_status()
            params['page'] += 1

    def get_organization(self, organization_id):
        """ Retrieves detailed data from an organization this API key has accessed to based on its ID.
        :param organization_id: string with the UUID-style unique ID of the organization
        :return: decoded JSON objects that represents the organization or None if not found
        """
        if not is_valid_uuid(organization_id):
            raise ValueError("organization id should be a string in UUID format")
        response = self._request_retry("GET", path='organizations/' + organization_id)
        if response.status_code == 200:
            return response.json()
        else:
            return None

    def get_organization_credentials(self, organization_id, cache=True):
        """ Retrieves a new set of temporary AWS credentials to allow access to an organization's S3 bucket.
        Typically used to upload log files. Will cache the response and return the same credentials if they
        have at least 10 minutes before expiration.
        :param organization_id: string with the UUID-style unique ID of the organization
        :param cache: boolean controlling whether credentials are cached in this connection
        :return: decoded JSON objects that represents the credentials
        """
        if not is_valid_uuid(organization_id):
            raise ValueError("organization id should be a string in UUID format")

        # try cached response first, must have at least 10 minutes validity
        if cache:
            cached_response = self._org_creds_cache.get(organization_id, None)
            if cached_response:
                exp = iso8601.parse_date(cached_response['expiration'])
                if exp >= (datetime.datetime.now(UTC) + datetime.timedelta(minutes=10)):
                    return cached_response
                else:
                    del self._org_creds_cache[organization_id]

        # get a new credential
        response = self._request_retry("GET", path='organizations/%s/credentials' % organization_id)
        if response.status_code == 200:
            cached_response = response.json()
            if cache:
                self._org_creds_cache[organization_id] = cached_response
            return cached_response
        else:
            response.raise_for_status()

    def iter_organization_alerts(self, organization_id, fromDate=None, toDate=None, sortBy="logDate", status=None):
        """ Generator that allows iteration over an organization's alerts, with optional filters.
        :param organization_id: string with the UUID-style unique ID of the organization
        :param fromDate: only list alerts with dates >= this parameter
        :param toDate: only list alerts with dates <= this parameter
        :param sortBy: one of 'logDate' or 'batchDate', controls which date field fromDate and toDate apply to
        :param status: a list or set containing one or more of 'new', 'under_investigation', 'rejected', 'resolved'
        :return: an iterator over the decoded JSON objects that represent alerts.
        """
        if not is_valid_uuid(organization_id):
            raise ValueError("organization id should be a string in UUID format")
        if sortBy is not None and not is_valid_alert_sortBy(sortBy):
            raise ValueError("sortBy must be either 'logDate' or 'batchDate'")
        if status is not None and not is_valid_alert_status(status):
            raise ValueError(
                "status must be an iterable with one or more of 'new', 'under_investigation', 'rejected' or 'resolved'")

        # loop over alert pages and yield them
        params = {
            'page': 1,
            'size': _PAGE_SIZE
        }
        if fromDate:
            params['fromDate'] = parse_date(fromDate)
        if toDate:
            params['toDate'] = parse_date(toDate)
        if sortBy:
            params['sortBy'] = sortBy
        if status:
            params['status'] = status

        while True:
            response = self._request_retry("GET", path='organizations/%s/alerts' % organization_id, params=params)
            if response.status_code == 200:
                alerts = response.json()
                for a in alerts:
                    yield a
                if len(alerts) < _PAGE_SIZE:
                    return
            elif response.status_code == 404:
                return
            else:
                response.raise_for_status()
            params['page'] += 1
