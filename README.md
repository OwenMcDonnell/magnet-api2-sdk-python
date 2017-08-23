# Niddel Magnet v2 API Python SDK

A simple client that allows idiomatic access to the 
[Niddel Magnet v2 REST API](https://api.niddel.com/v2). Uses the wonderful
[requests](http://docs.python-requests.org/) package to perform the requests.

## Configuring Credentials

There are a couple of ways to let the `Connection` object know which API key to use.
The simplest one is to pass one explicitly to its constructor:
```python
from magnetsdk2 import Connection

conn = Connection(api_key="my secret API key")
```

If an explicit API key is not provided, the `Connection` constructor will look for 
one first in the `MAGNETSDK_API_KEY` environment variable and failing that in the 
`default` profile of the configuration file.

You can add different API keys to a configuration file with different profiles by
creating a file called `.magnetsdk/config` under the current user's home directory.
It is a basic Python configuration file that looks like the following:

```
[default]
api_key=my secret api key

[profile2]
api_key=another secret api key
```

So in this case you could create a connection to use either API key as follows:
```python
from magnetsdk2 import Connection

conn_default = Connection()                     # uses default profile
conn_profile2 = Connection(profile='profile2')  # use profile2 explicitly
```

## Using the SDK

It's as simple as creating a `Connection` object and using it to perform queries.
This small example shows you how to print out all of the organizations the configured
API key has access to.
```python
import json
from magnetsdk2 import Connection

conn = Connection()
for org in conn.iter_organizations():
    print(json.dumps(org, indent=4))
``` 

## Downloading Only New Alerts

A common scenario for using the SDK is downloading only new alerts over time, typically
to feed an integration with a 3rd party SIEM or ticketing system. In order to implement 
this, the concept of a persistent iterator that saves its state on a JSON file is provided 
in the SDK:

```python
from magnetsdk2 import Connection
from magnetsdk2.iterator import FilePersistentAlertIterator

conn = Connection()
alert_iterator = FilePersistentAlertIterator('persistence.json', conn, 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx')
for alert in alert_iterator:
    print(alert)
    try:
        # try to process alert in same way
        print(alert)
    except:
        alert_iterator.load()   # on failure, reload iterator to ignore latest consumed alert
    else:
        alert_iterator.save()   # on success, persist the current iterator state
```

If you run this same code multiple times, it will ever only output alerts it hasn't 
processed before, provided file `persistence.json` is not tampered with and remains 
available for reading and writing.

You save the current state of the iterator with the `save` method. If you tried to
processing alerts and failed, you can simply not save the iterator and reload the
previous consistent state from disk using the `load` method.

Though the provided implementation saves the data to a JSON file, it is easy to add other
means of persistence by creating subclasses of 
`magnetsdk2.iterator.AbstractPersistentAlertIterator` that implement the abstract `_save`
and `_load` methods.
