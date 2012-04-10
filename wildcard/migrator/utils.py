from plone.app.redirector.interfaces import IRedirectionStorage
from zope.component import getUtility
from zope.app.component.hooks import getSite
from wildcard.migrator import mjson as json


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
    args = request.get('args')
    if args:
        args = json.loads(args)
        for key, val in args.items():
            del args[key]
            args[str(key)] = val
    else:
        args = {}
    if migrator._type in ['object', 'folder', '_']:
        path = request.get('path', '')
        context = safeTraverse(site, str(path), None)
        if not context:
            redirect_storage = getUtility(IRedirectionStorage)
            site_path = '/'.join(site.getPhysicalPath())
            newpath = redirect_storage.get(
                site_path + '/' + path.lstrip('/'), None)
            if newpath:
                context = safeTraverse(site, newpath, None)
            if not context:
                context = path
        migrator = migrator(site, context, **args)
    else:
        migrator = migrator(site, None, **args)
    return migrator


def safeTraverse(context, path, default=None):
    """
    traverse through objects without picking
    up views and other things that acquisition
    picks up along the way
    """
    objectids = path.strip('/').split('/')
    try:
        for objid in objectids:
            context = context[objid]
    except KeyError:
        return default
    return context
