from wildcard.migrator.utils import convertListOfDicts
from wildcard.migrator import BaseMigrator
from wildcard.migrator import addMigrator


class ObjectPropertiesMigrator(BaseMigrator):
    title = "Object Properties"
    _type = 'object'

    @classmethod
    def _get(kls, obj):
        try:
            structure = convertListOfDicts(obj._properties)
        except AttributeError:
            return {
                'structure': {},
                'values': []
            }
        values = obj.propertyItems()
        return {
            'structure': structure,
            'values': values
        }

    @classmethod
    def _set(kls, obj, value):
        structure = value['structure']
        values = value['values']

        if not structure or not values:
            return
        existing_structure = convertListOfDicts(obj._properties)
        for id, struct in structure.items():
            if id not in existing_structure:
                existing_structure[id] = struct
            else:
                existing_structure[id].update(struct)

        obj._properties = tuple(existing_structure.values())

        for key, value in values:
            if existing_structure[key]['type'] == 'string':
                # try to convert to string if possible
                try:
                    value = str(value)
                except:
                    pass
            setattr(obj, key, value)
addMigrator(ObjectPropertiesMigrator)
