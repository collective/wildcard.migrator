from wildcard.migrator import BaseMigrator

_skipped_fields = ['id']


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
                'value': field.get(obj, raw=True),
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
