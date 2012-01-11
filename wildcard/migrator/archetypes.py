from wildcard.migrator import addMigrator
from wildcard.migrator import BaseMigrator
from plone.app.blob.field import BlobWrapper
from wildcard.migrator import mjson as json
from Products.Archetypes.Field import Image
try:
    from Products.Archetypes.interfaces._base import IBaseObject
except:
    from Products.Archetypes.interfaces.base import IBaseObject
from Products.Archetypes.BaseUnit import BaseUnit
from OFS.Image import File
from OFS.Image import Image as OFSImage
from zope.app.component.hooks import getSite
from persistent.list import PersistentList

_skipped_fields = ['id']


def _convert(value, safe=True):
    if isinstance(value, BlobWrapper) or isinstance(value, Image) or \
            isinstance(value, File) or isinstance(value, OFSImage):
        return json._filedata_marker + json._deferred_marker
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


class FieldsMigrator(BaseMigrator):
    title = 'Fields'
    _type = 'object'

    @classmethod
    def _get(kls, obj):
        fields = {}
        for field in obj.Schema().fields():
            if field.__name__ in _skipped_fields:
                continue
            fields[field.__name__] = FieldMigrator._get(obj, field.__name__)
        return fields

    @classmethod
    def _set(kls, obj, values):
        for name, value in values.items():
            if name in _skipped_fields:
                continue
            value = FieldMigrator._set(obj, value, name)
addMigrator(FieldsMigrator)


class FieldMigrator(BaseMigrator):
    title = 'Field'
    _type = 'object'

    def __init__(self, site, obj, fieldname, safe=True):
        self.site = site
        self.obj = obj
        self.fieldname = fieldname
        self.safe = safe

    def get(self):
        return self._get(self.obj, self.fieldname, self.safe)

    @classmethod
    def _get(kls, obj, fieldname, safe=True):
        field = obj.getField(fieldname)
        if getattr(field, 'default_output_type', None) == \
                                                    'text/x-html-safe':
            extras = {'mimetype': 'text/html', 'field': 'text'}
        else:
            extras = {}
        return {
            'value': _convert(field.get(obj, raw=True), safe),
            'extras': extras
        }

    def set(self, value):
        self._set(self.obj, value, self.fieldname)

    @classmethod
    def _set(kls, obj, value, fieldname):
        field = obj.getField(fieldname)
        if not field or value['value'] == json.Deferred:
            return
        val = value['value']
        try:
            field.set(obj, val, **value['extras'])
        except AttributeError:
            # ignore errors on setting empty values. Otherwise, raise
            if val is not None and val != False:
                raise

addMigrator(FieldMigrator)
