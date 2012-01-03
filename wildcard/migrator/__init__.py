

class BaseMigrator(object):

    title = None
    # available contexts:
    #   site, object, folder, gs, *
    _type = None

    def __init__(self, site, obj=None):
        self.site = site
        self.obj = obj

    @classmethod
    def _get(self, obj):
        raise Exception("Not implemented")

    def get(self):
        return self._get(self.obj)

    @classmethod
    def _set(kls, obj, value):
        raise Exception("Not implemented")

    def set(self, value):
        return self._set(self.obj, value)


_migrators = []


def addMigrator(kls):
    _migrators.append(kls)


def getMigrators():
    return _migrators


def getMigrator(title):
    for mgr in _migrators:
        if mgr.title == title:
            return mgr


def getMigratorsOfType(_type):
    for kls in _migrators:
        if kls._type == _type:
            yield kls


def scan():
    from wildcard.migrator import properties
    from wildcard.migrator import archetypes
    from wildcard.migrator import content
    from wildcard.migrator import workflow
    from wildcard.migrator import gs