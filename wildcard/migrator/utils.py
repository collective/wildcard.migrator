from zope.app.component.hooks import getSite


def convertListOfDicts(tup):
    key = 'id' in tup[0] and 'id' or tup[0].keys()[0]
    dic = {}
    for val in tup:
        dic[val[key]] = val
    return dic


def getMigratorFromRequest(request):
    from wildcard.migrator import getMigrator

    migrator = request.get('migrator')
    if not migrator:
        raise Exception("Must specify a migrator")

    migrator = getMigrator(migrator)
    site = getSite()
    if migrator._type in ['object', 'folder', '_']:
        path = request.get('path')
        context = site.unrestrictedTraverse(str(path), None)
        if not context:
            context = path
        migrator = migrator(site, context)
    else:
        migrator = migrator(site)
    return migrator
