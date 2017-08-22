from collections import Iterable, Iterator
from abc import ABCMeta, abstractmethod
import json
from os.path import isfile

from validation import is_valid_uuid, parse_date
from connection import Connection


class PersistenceEntry(object):
    """Class that encapsulates the minimal persistence information needed to continously process
    only new alerts from a given organization."""

    @property
    def organization_id(self):
        """A string in UUID format containing the ID of the organization."""
        return self._organization_id

    @organization_id.setter
    def organization_id(self, organization_id):
        if not is_valid_uuid(organization_id):
            raise ValueError('invalid organization ID')
        self._organization_id = organization_id

    @property
    def latest_batch_date(self):
        """A string representing a date in ISO8601 format, which indicates the most recent batch date
        that has already been processed."""
        return self._latest_batch_date

    @latest_batch_date.setter
    def latest_batch_date(self, latest_batch_date):
        if latest_batch_date is None:
            self._latest_batch_date = None
        else:
            self._latest_batch_date = parse_date(latest_batch_date)

    @property
    def latest_alert_ids(self):
        """A set of string in UUID format that indicate which alerts on the latest batch date
        have already been processed."""
        return self._latest_alert_ids

    @latest_alert_ids.setter
    def latest_alert_ids(self, latest_alert_ids):
        if latest_alert_ids is None:
            self._latest_alert_ids = set()
        else:
            if not isinstance(latest_alert_ids, Iterable):
                raise ValueError('latest alert IDs must be iterable')
            if len(latest_alert_ids) > 0 and not all(is_valid_uuid(x) for x in latest_alert_ids):
                raise ValueError('latest alert IDs must only contain UUIDs')
            self._latest_alert_ids = {x for x in latest_alert_ids}

    def add_alert_id(self, alert_id):
        if not is_valid_uuid(alert_id):
            raise ValueError("invalid alert ID")
        self._latest_alert_ids.add(alert_id)

    def __init__(self, organization_id, latest_batch_date=None, latest_alert_ids=None):
        self.organization_id = organization_id
        self.latest_batch_date = latest_batch_date
        self.latest_alert_ids = latest_alert_ids


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
        self._persistence_entry = self.load(organization_id)
        if not isinstance(self._persistence_entry, PersistenceEntry):
            raise ValueError('load method should return a PersistenceEntry instance')
        if not self._persistence_entry.organization_id == organization_id:
            raise ValueError('PersistenceEntry instance does not match organization ID ' + organization_id)

        if start_date is not None:
            start_date = parse_date(start_date)
            if self._persistence_entry.latest_batch_date is None \
                    or self._persistence_entry.latest_batch_date < start_date:
                self._persistence_entry.latest_batch_date = start_date
                self._persistence_entry.latest_alert_ids = None
        self._alerts = []

    @abstractmethod
    def load(self, organization_id):
        """Abstract method that loads a given organization's persistence data."""
        pass

    @abstractmethod
    def save(self, persistence_entry):
        """Abstract method that saves a given organization's persistence data."""
        pass

    def __iter__(self):
        return self

    def _load_alerts(self):
        # if we already have cached alerts, do nothing
        if self._alerts:
            return

        # get the candidate dates in order, and discard the ones we've already fully processed
        dates = sorted([x for x in
                        self._connection.list_organization_alert_dates(self._persistence_entry.organization_id,
                                                                       'batchDate')])
        if self._persistence_entry.latest_batch_date:
            dates = [x for x in dates if x >= self._persistence_entry.latest_batch_date]

        # loop over candidate dates
        for d in dates:
            # if candidate date is newer, reset persistence data to it
            if d != self._persistence_entry.latest_batch_date:
                self._persistence_entry.latest_batch_date = d
                self._persistence_entry.latest_alert_ids = None

            # add any alerts on the candidate date we haven't processed yet to the cache
            for alert in self._connection.iter_organization_alerts(
                    organization_id=self._persistence_entry.organization_id,
                    fromDate=d, toDate=d, sortBy='batchDate'):
                if alert['id'] not in self._persistence_entry.latest_alert_ids:
                    self._alerts.append(alert)

            # if alert cache is not empty, we are finished for now
            if self._alerts:
                return

    def next(self):
        if not self._alerts:
            self._load_alerts()

        if self._alerts:
            alert = self._alerts.pop()
            self._persistence_entry.latest_batch_date = alert['batchDate']
            self._persistence_entry.add_alert_id(alert['id'])
            self.save(self._persistence_entry)
            return alert
        else:
            raise StopIteration


class FilePersistentAlertIterator(AbstractPersistentAlertIterator):
    """Subclass of AbstractPersistentAlertIterator that saves the persistence state as a JSON object
    on a given text file. Does not lock the file or otherwise prevent multiple processes corrupting
    the state, so any such control is left up to the caller. Assumes one file per organization, as
    the save method completely overwrites the file contents."""
    def __init__(self, filename, connection, organization_id, start_date=None):
        self._filename = filename
        super(FilePersistentAlertIterator, self).__init__(connection, organization_id, start_date)

    def load(self, organization_id):
        if not isfile(self._filename):
            pe = PersistenceEntry(organization_id)
            self.save(pe)
            return pe
        else:
            with open(self._filename, 'r') as f:
                pe = json.load(f)
                return PersistenceEntry(pe['organization_id'], pe['latest_batch_date'], pe['latest_alert_ids'])

    def save(self, persistence_entry):
        pe = {
            'organization_id': persistence_entry.organization_id,
            'latest_batch_date': persistence_entry.latest_batch_date,
            'latest_alert_ids': [x for x in persistence_entry.latest_alert_ids]
        }
        with open(self._filename, 'w') as f:
            json.dump(pe, f)
