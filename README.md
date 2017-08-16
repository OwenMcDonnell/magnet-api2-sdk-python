# Niddel Magnet v2 API Python SDK

A simple client that allows idiomatic access to the 
[Niddel Magnet v2 REST API](https://api.niddel.com/v2). Uses the wonderful
[requests](http://docs.python-requests.org/) package to perform the requests.

## Using the SDK

It's as simple as creating a `Connection` object and using it to perform queries.
This small example shows you how to print out all of the organizations the configured
API key has access to.
```python
import json
from magnetsdk2 import Connection

conn = Connection()
for org in conn.organizations()
    print json.dumps(org, indent=4)
``` 

## Configuring Credentials

There are a couple of ways to let the `Connection` object know which API key to use.
The simplest one is to pass one explicitly to its constructor:
```python
conn = magnetsdk2.Connection(api_key="my secret API key")
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
conn_default = Connection()   # uses default profile
conn_profile2 = Connection(profile='profile2')
```
