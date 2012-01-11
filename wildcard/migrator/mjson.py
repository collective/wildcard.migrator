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
from zope.dottedname.resolve import resolve

import OFS


_filedata_marker = 'filedata://'
_deferred_marker = 'deferred://'
_type_marker = 'type://'
_uid_marker = 'uid://'
_uid_separator = '||||'
_date_re = re.compile('^[0-9]{4}\-[0-9]{2}\-[0-9]{2}.*$')


class BaseTypeSerializer(object):
    klass = None
    toklass = None

    @classmethod
    def getTypeName(kls):
        return "%s.%s" % (kls.klass.__module__, kls.klass.__name__)

    @classmethod
    def serialize(self, obj):
        if hasattr(obj, 'aq_base'):
            obj = obj.aq_base
        data = self._serialize(obj)
        results = {
            'type': self.getTypeName(),
            'data': data
        }
        return _type_marker + dumps(results)

    @classmethod
    def _serialize(self, obj):
        return self.toklass(obj)

    @classmethod
    def deserialize(self, data):
        return self._deserialize(data)

    @classmethod
    def _deserialize(self, data):
        return self.klass(data)


class PersistentMappingSerializer(BaseTypeSerializer):
    klass = PersistentMapping
    toklass = dict


class PersistentDictSerializer(BaseTypeSerializer):
    klass = PersistentDict
    toklass = dict


class OOBTreeSerializer(BaseTypeSerializer):
    klass = OOBTree
    toklass = dict


class PersistentListSerializer(BaseTypeSerializer):
    klass = PersistentList
    toklass = list


class setSerializer(BaseTypeSerializer):
    klass = set
    toklass = list


class OFSFileSerializer(BaseTypeSerializer):
    klass = OFS.Image.File

    @classmethod
    def _serialize(self, obj):
        try:
            data = str(obj.data)
        except:
            data = str(obj.data.data)

        return {
            'data': base64.b64encode(data),
            'id': obj.id(),
            'title': obj.title,
            'content_type': obj.content_type
        }

    @classmethod
    def _deserialize(self, data):
        file = base64.b64decode(data['data'])
        id = data['id']
        title = data['title']
        ct = data['content_type']
        return self.klass(id, title, file, ct)


class OFSImageSerializer(OFSFileSerializer):
    klass = OFS.Image.Image


class DateTimeSerializer(BaseTypeSerializer):
    klass = DateTime

    @classmethod
    def getTypeName(kls):
        return 'DateTime.DateTime'

    @classmethod
    def _serialize(self, obj):
        return obj.ISO8601()

    @classmethod
    def _deserialize(self, data):
        return DateTime(data)


class datetimeSerializer(BaseTypeSerializer):
    klass = datetime

    @classmethod
    def _serialize(self, obj):
        return obj.isoformat()

    @classmethod
    def _deserialize(self, data):
        return datetime.strptime(data, '%Y-%m-%dT%H:%M:%S.%f')


_serializers = {
    PersistentMapping: PersistentMappingSerializer,
    PersistentDict: PersistentDictSerializer,
    OOBTree: OOBTreeSerializer,
    PersistentList: PersistentListSerializer,
    set: setSerializer,
    OFS.Image.Image: OFSImageSerializer,
    OFS.Image.File: OFSFileSerializer,
    DateTime: DateTimeSerializer,
    datetime: datetimeSerializer
}


class Deferred:
    pass


def customhandler(obj):
    _type = type(obj)
    if _type.__name__ == 'instance':
        _type = obj.__class__
    if _type in _serializers:
        serializer = _serializers[_type]
        return serializer.serialize(obj)
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
                if v == _filedata_marker + _deferred_marker:
                    v = Deferred
                else:
                    v = StringIO(base64.b64decode(v[len(_filedata_marker):]))
            elif v.startswith(_type_marker):
                v = v[len(_type_marker):]
                results = loads(v)
                _type = resolve(results['type'])
                serializer = _serializers[_type]
                v = serializer.deserialize(results['data'])
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
