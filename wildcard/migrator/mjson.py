try:
    import json
except ImportError:
    import simplejson as json
from datetime import datetime
from DateTime import DateTime
from plone.app.blob.field import BlobWrapper
from StringIO import StringIO
import base64
from persistent.dict import PersistentDict
from zope.app.component.hooks import getSite
try:
    from Persistence.mapping import PersistentMapping
except:
    from persistent.mapping import PersistentMapping
from persistent.list import PersistentList
from Products.Archetypes.Field import Image
try:
    from Products.Archetypes.interfaces._base import IBaseObject
except:
    from Products.Archetypes.interfaces.base import IBaseObject

_filedata_marker = 'filedata://'
_uid_marker = 'uid://'
_uid_separator = '||||'


def customhandler(obj):
    if isinstance(obj, datetime):
        return DateTime(obj).ISO8601()
    elif isinstance(obj, DateTime):
        return obj.ISO8601()
    elif isinstance(obj, BlobWrapper) or isinstance(obj, Image):
        return _filedata_marker + base64.b64encode(obj.data)
    elif isinstance(obj, PersistentDict) or isinstance(obj, PersistentMapping):
        return dict(obj.copy())
    elif isinstance(obj, PersistentList):
        return [i for i in obj]
    elif hasattr(obj, 'UID'):
        if IBaseObject.providedBy(obj):
            site_path = '/'.join(getSite().getPhysicalPath())
            return '%s%s%s%s' % (
                _uid_marker, obj.UID(),
                _uid_separator,
                '/'.join(obj.getPhysicalPath())[len(site_path) + 1:]
            )
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
    try:
        return json.dumps(data, default=customhandler)
    except:
        import pdb; pdb.set_trace()
        raise
