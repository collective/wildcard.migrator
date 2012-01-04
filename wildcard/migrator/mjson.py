try:
    import json
except ImportError:
    import simplejson as json
from datetime import datetime
from DateTime import DateTime
from StringIO import StringIO
import base64
from persistent.dict import PersistentDict
try:
    from Persistence.mapping import PersistentMapping
except:
    from persistent.mapping import PersistentMapping
from persistent.list import PersistentList
from BTrees.OOBTree import OOBTree
import re

_filedata_marker = 'filedata://'
_uid_marker = 'uid://'
_uid_separator = '||||'
_date_re = re.compile('^[0-9]{4}\-[0-9]{2}\-[0-9]{2}.*$')


def customhandler(obj):
    if isinstance(obj, datetime):
        return DateTime(obj).ISO8601()
    elif isinstance(obj, DateTime):
        return obj.ISO8601()
    elif isinstance(obj, PersistentDict) or \
            isinstance(obj, PersistentMapping) or \
            isinstance(obj, OOBTree):
        return dict(obj.copy())
    elif isinstance(obj, PersistentList) or isinstance(obj, set):
        return [i for i in obj]
    return obj


def decodeUid(v):
    v = v[len(_uid_marker):]
    return v.split(_uid_separator)


def custom_decoder(d):
    if isinstance(d, list):
        pairs = enumerate(d)
    elif isinstance(d, dict):
        pairs = d.items()
    result = []
    for k, v in pairs:
        if isinstance(v, basestring):
            if v.startswith(_filedata_marker):
                v = StringIO(base64.b64decode(v[len(_filedata_marker):]))
            else:
                if _date_re.match(v):
                    try:
                        v = DateTime(v)
                    except:
                        pass
        elif isinstance(v, (dict, list)):
            v = custom_decoder(v)
        result.append((k, v))
    if isinstance(d, list):
        return [x[1] for x in result]
    elif isinstance(d, dict):
        return dict(result)


def loads(data):
    return json.loads(data, object_hook=custom_decoder)


def dumps(data):
    return json.dumps(data, default=customhandler)
