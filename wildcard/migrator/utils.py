from plone.app.redirector.interfaces import IRedirectionStorage
from zope.component import getUtility
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
            redirect_storage = getUtility(IRedirectionStorage)
            site_path = '/'.join(site.getPhysicalPath())
            newpath = redirect_storage.get(
                site_path + '/' + path.lstrip('/'), None)
            if newpath:
                context = site.unrestrictedTraverse(newpath, None)
            if not context:
                context = path
        migrator = migrator(site, context)
    else:
        migrator = migrator(site)
    return migrator
