# -*- coding: utf-8 -*-
"""
This module allows persistent iteration of alerts. Some use cases include opening tickets based
on new alerts, or even automating responses for some high-confidence alerts.
"""
import json
from abc import ABCMeta, abstractmethod
from collections import Iterable, Iterator
from os.path import isfile

from six import python_2_unicode_compatible

from magnetsdk2.connection import Connection
from magnetsdk2.validation import is_valid_uuid, parse_date, parse_timestamp


@python_2_unicode_compatible
class PersistenceEntry(object):
    """Class that encapsulates the minimal persistence information needed to continously process
    only new alerts from a given organization."""

    @property
    def organization_id(self):
        """A string in UUID format containing the ID of the organization."""
        return self._organization_id

    @property
    def latest_batch_date(self):
        """A string representing a date in ISO8601 format, which indicates the most recent batch
        date that has already been processed."""
        return self._latest_batch_date

    @latest_batch_date.setter
    def latest_batch_date(self, latest_batch_date):
        if latest_batch_date is None:
            self._latest_batch_date = None
        else:
            self._latest_batch_date = latest_batch_date

    @property
    def latest_api_cursor(self):
        """A string representing the most recent alerts that has already been processed."""
        return self._latest_api_cursor

    @latest_api_cursor.setter
    def latest_api_cursor(self, latest_api_cursor):
        if latest_api_cursor is None:
            self._latest_api_cursor = None
        else:
            self._latest_api_cursor = latest_api_cursor

    @property
    def latest_alert_ids(self):
        """A set of string in UUID format that indicate which alerts on the latest batch date
        have already been processed."""
        return self._latest_alert_ids

    @latest_alert_ids.setter
    def latest_alert_ids(self, latest_alert_ids):
        if latest_alert_ids is None:
            self._latest_alert_ids = []
        else:
            if not isinstance(latest_alert_ids, list):
                latest_alert_ids = [latest_alert_ids]
            if not isinstance(latest_alert_ids, Iterable):
                raise ValueError('latest alert IDs must be iterable')
            if latest_alert_ids and not all(is_valid_uuid(x) for x in latest_alert_ids):
                raise ValueError('latest alert IDs must only contain UUIDs')
            self._latest_alert_ids = [x for x in latest_alert_ids]

    def add_alert_id(self, alert_id):
        if not is_valid_uuid(alert_id):
            raise ValueError("invalid alert ID")
        self._latest_alert_ids.append(alert_id)

    def __init__(self, organization_id, latest_batch_date=None, latest_alert_ids=None, latest_api_cursor=None):
        if not is_valid_uuid(organization_id):
            raise ValueError('invalid organization ID')
        self._organization_id = organization_id
        self._latest_batch_date = None
        self._latest_api_cursor = None
        self._latest_alert_ids = []
        self.latest_batch_date = latest_batch_date
        self.latest_api_cursor = latest_api_cursor
        self.latest_alert_ids = latest_alert_ids

    def __str__(self):
        return "%s(organization_id=%s, latest_batch_date=%s, latest_alert_ids=%s, latest_api_cursor=%s)" \
               % (self.__class__.__name__, self.organization_id, self.latest_batch_date,
                  self.latest_alert_ids, self.latest_api_cursor)


@python_2_unicode_compatible
class AbstractPersistentAlertIterator(Iterator):
    """Abstract class that encapsulates the logic of walking through an organization's alerts in
    increasing batch date order and persisting state the prevents an alert from being seen multiple
    times across executions."""

    __metaclass__ = ABCMeta

    def __init__(self, connection, organization_id, start_date=None):
        """Initializes a persistent alert iterator.
        :param connection: an instance of magnetsdk2.Connection
        :param organization_id: a string containing an organization ID in UUID format
        :param start_date: optional date that represents the initial batch date to load alerts from
        """
        if not isinstance(connection, Connection):
            raise ValueError('invalid connection')
        self._connection = connection

        if not is_valid_uuid(organization_id):
            raise ValueError('invalid organization ID')
        self._organization_id = organization_id

        if start_date is not None:
            self._start_date = parse_timestamp(start_date)
        else:
            self._start_date = None
        self._persistence_entry = None
        self._alerts = []

    @property
    def organization_id(self):
        return self._organization_id

    @property
    def start_date(self):
        return self._start_date

    @property
    def connection(self):
        return self._connection

    @property
    def persistence_entry(self):
        if not self._persistence_entry:
            self._persistence_entry = self._load()
            if self._persistence_entry is None:
                self._persistence_entry = PersistenceEntry(self.organization_id)
            else:
                if not isinstance(self._persistence_entry, PersistenceEntry):
                    raise ValueError('load method should return a PersistenceEntry instance')
                if not self._persistence_entry.organization_id == str(self.organization_id):
                    raise ValueError(
                        'PersistenceEntry instance does not match organization ID ' \
                        + self.organization_id)

            if self._start_date:
                if self._persistence_entry.latest_batch_date is None \
                        or self._persistence_entry.latest_batch_date < self._start_date:
                    self._persistence_entry.latest_batch_date = self._start_date
                    self._persistence_entry.latest_api_cursor = None
                    self._persistence_entry.latest_alert_ids = None

        return self._persistence_entry

    @abstractmethod
    def _load(self):
        """Abstract method that loads a given organization's persistence data. Implementations
        should return a PersistenceEntry instance or None."""
        pass

    @abstractmethod
    def _save(self):
        """Abstract method that saves a given organization's persistence data."""
        pass

    def __iter__(self):
        return self

    def _load_alerts(self):
        # if we already have cached alerts, do nothing
        if self._alerts:
            return

        if self.persistence_entry.latest_api_cursor:
            alerts_generator = self._connection.iter_organization_alerts_stream(
                                    organization_id=self._persistence_entry.organization_id,
                                    latest_api_cursor=self._persistence_entry.latest_api_cursor,
                                    persistence=True)
        else:
            latest_batch_date = self.persistence_entry.latest_batch_date
            alerts_generator = self._connection.iter_organization_alerts_stream(
                                    organization_id=self._persistence_entry.organization_id,
                                    latest_batch_date=latest_batch_date,
                                    persistence=True)

        for alert in alerts_generator:
            if not alert['alert']['id'] in self._persistence_entry._latest_alert_ids:
                self._alerts.append(alert)

        # if alert cache is not empty, we are finished for now
        if self._alerts:
            return

    def save(self):
        self._save()

    def load(self):
        self._persistence_entry = None
        self._alerts = []

    def next(self):
        if not self._alerts:
            self._load_alerts()

        if self._alerts:
            alert = self._alerts.pop()
            self._persistence_entry.latest_api_cursor = alert['cursor']
            self._persistence_entry.latest_batch_date = str(alert['alert']['batchDate'] +'T'+ alert['alert']['batchTime'])
            self._persistence_entry.add_alert_id(alert['alert']['id'])
            return alert['alert']
        else:
            raise StopIteration

    def __str__(self):
        return "%s(organization_id=%s, start_date=%s, persistence_entry=%s)" \
               % (self.__class__.__name__, self.organization_id, self.start_date,
                  self.persistence_entry)


@python_2_unicode_compatible
class FilePersistentAlertIterator(AbstractPersistentAlertIterator):
    """Subclass of AbstractPersistentAlertIterator that saves the persistence state as a JSON object
    on a given text file. Does not lock the file or otherwise prevent multiple processes corrupting
    the state, so any such control is left up to the caller. Assumes one file per organization, as
    the save method completely overwrites the file contents."""

    def __init__(self, filename, *args, **kwargs):
        self._filename = filename
        super(FilePersistentAlertIterator, self).__init__(*args, **kwargs)

    @property
    def filename(self):
        return self._filename

    def _load(self):
        if isfile(self._filename):
            with open(self._filename, 'r') as f:
                pe = json.load(f)
                if pe.has_key('latest_batch_date'):
                    return PersistenceEntry(pe['organization_id'], pe['latest_batch_date'],
                                        pe['latest_alert_ids'], None)
                if pe.has_key('latest_api_cursor'):
                    return PersistenceEntry(pe['organization_id'], None,
                                        pe['latest_alert_ids'], pe['latest_api_cursor'])
        else:
            return None

    def _save(self):
        pe = {
            'organization_id': str(self.persistence_entry.organization_id),
            'latest_api_cursor': self.persistence_entry.latest_api_cursor,
            'latest_alert_ids': self.persistence_entry.latest_alert_ids[-1]
        }
        with open(self._filename, 'w') as f:
            json.dump(pe, f)

    def __str__(self):
        return super(FilePersistentAlertIterator, self).__str__()[:-1] + ", filename=%s)" \
                                                                         % self._filename
