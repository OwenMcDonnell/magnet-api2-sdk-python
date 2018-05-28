# -*- coding: utf-8 -*-
"""
This module allows persistent iteration of alerts. Some use cases include opening tickets based
on new alerts, or even automating responses for some high-confidence alerts.
"""

import json
from datetime import datetime, timedelta
from abc import ABCMeta, abstractmethod
from collections import Iterable, Iterator
from os.path import isfile

from six import python_2_unicode_compatible

from magnetsdk2.connection import Connection
from magnetsdk2.validation import is_valid_uuid, parse_date


@python_2_unicode_compatible
class PersistenceEntry(object):
    """Class that encapsulates the minimal persistence information needed to continously process
    only new alerts from a given organization."""

    @property
    def organization_id(self):
        """A string in UUID format containing the ID of the organization."""
        return self._organization_id

    @property
    def latest_alert_id(self):
        """A tuple of string in UUID format indicating the alert ID and a 
        string in DateTime UTC format indicating the alert created date."""
        return self._latest_alert_id

    @latest_alert_id.setter
    def latest_alert_id(self, latest_alert_id):
        if latest_alert_id is None:
            self._latest_alert_id = None
        else:
            if not isinstance(latest_alert_id, Iterable):
                raise ValueError("iterator.latest_alert_id.setter': latest alert ID must be iterable")
            if latest_alert_id and not is_valid_uuid(latest_alert_id):
                raise ValueError("iterator.latest_alert_id.setter': latest alert ID must only contain UUIDs")
            self._latest_alert_id = latest_alert_id

    def update_alert_id(self, alert_id):
        if not is_valid_uuid(alert_id):
            raise ValueError("'iterator.update_alert_id': invalid alert ID")
        self._latest_alert_id = alert_id

    def __init__(self, organization_id, latest_alert_id=None):
        if not is_valid_uuid(organization_id):
            raise ValueError("iterator.__init__': invalid organization ID")

        self._organization_id = organization_id
        self._latest_alert_id = None
        self.latest_alert_id = latest_alert_id

    def __str__(self):
        return "%s(organization_id=%s, latest_alert_id=%s)" \
               % (self.__class__.__name__, self.organization_id, self.latest_alert_id)


@python_2_unicode_compatible
class AbstractPersistentAlertIterator(Iterator):
    """Abstract class that encapsulates the logic of walking through an organization's alerts in
    increasing batch date order and persisting state the prevents an alert from being seen multiple
    times across executions."""

    __metaclass__ = ABCMeta

    def __init__(self, connection, organization_id):
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
        self._persistence_entry = None
        self._alerts = []

    @property
    def organization_id(self):
        return self._organization_id

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
                if not self._persistence_entry.organization_id == self.organization_id:
                    raise ValueError(
                        'PersistenceEntry instance does not match organization ID ' \
                        + self.organization_id)

            #if self._start_date:
            #        self._persistence_entry.latest_alert_id = None

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

        if self.persistence_entry.latest_alert_id:
            latest_alert_id = self.persistence_entry.latest_alert_id
        else:
            latest_alert_id = None

        if self.persistence_entry.organization_id:
            org_id = self._persistence_entry.organization_id

        for alert in self._connection.iter_organization_alerts_stream(
            organization_id=org_id, alert_id=latest_alert_id):
            self._alerts.append(alert)

            # if alert cache is empty, we are finished for now
            if not self._alerts:
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
            if self._persistence_entry._latest_alert_id:
                self._persistence_entry.update_alert_id(alert['id'])
            return alert
        else:
            raise StopIteration

    def __str__(self):
        return "%s(organization_id=%s, persistence_entry=%s)" \
               % (self.__class__.__name__, self.organization_id, self.persistence_entry)


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
            ipdb.set_trace()
            with open(self._filename, 'r') as f:
                pe = json.load(f)
                return PersistenceEntry(pe['organization_id'], pe['latest_alert_id'])
        else:
            return None

    def _save(self):
        """Once 'self._persistence_entry.latest_alert_ids' is a tuple, it is required to convert it to a
        dictionary aggregated by unique 'created at' datetime."""
        pe = {
            'organization_id': str(self.persistence_entry.organization_id),
            'latest_alert_id': self._persistence_entry.latest_alert_id
        }
        ipdb.set_trace()
        with open(self._filename, 'w') as f:
            json.dump(pe, f)

    def __str__(self):
        return super(FilePersistentAlertIterator, self).__str__()[:-1] + ", filename=%s)" \
                                                                         % self._filename
