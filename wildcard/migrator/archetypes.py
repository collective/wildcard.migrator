from wildcard.migrator import BaseMigrator
from plone.app.blob.field import BlobWrapper
from wildcard.migrator import mjson as json
from Products.Archetypes.Field import Image
try:
    from Products.Archetypes.interfaces._base import IBaseObject
except:
    from Products.Archetypes.interfaces.base import IBaseObject
from Products.Archetypes.BaseUnit import BaseUnit
import base64
from zope.app.component.hooks import getSite
from persistent.list import PersistentList


_skipped_fields = ['id']


def _convert(value):
    if isinstance(value, BlobWrapper) or isinstance(value, Image):
        return json._filedata_marker + base64.b64encode(value.data)
    elif isinstance(value, BaseUnit):
        return value.getRaw()
    elif hasattr(value, 'UID'):
        if IBaseObject.providedBy(value):
            site_path = '/'.join(getSite().getPhysicalPath())
            return '%s%s%s%s' % (
                json._uid_marker, value.UID(),
                json._uid_separator,
                '/'.join(value.getPhysicalPath())[len(site_path) + 1:]
            )
    elif type(value) in (list, tuple, set, PersistentList):
        return [_convert(v) for v in value]
    return value


class FieldMigrator(BaseMigrator):

    @classmethod
    def _get(kls, obj):
        fields = {}
        for field in obj.Schema().fields():
            if field.__name__ in _skipped_fields:
                continue
            if getattr(field, 'default_output_type', None) == \
                                                    'text/x-html-safe':
                extras = {'mimetype': 'text/html', 'field': 'text'}
            else:
                extras = {}
            fields[field.__name__] = {
                'value': _convert(field.get(obj, raw=True)),
                'extras': extras
            }
        return fields

    @classmethod
    def _set(kls, obj, values):
        for name, value in values.items():
            if name in _skipped_fields:
                continue
            field = obj.getField(name)
            if not field:
                continue
            field.set(obj, value['value'], **value['extras'])
