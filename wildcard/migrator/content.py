from Products.CMFCore.utils import getToolByName
from wildcard.migrator import addMigrator
from wildcard.migrator import BaseMigrator
from wildcard.migrator.archetypes import FieldsMigrator
from wildcard.migrator.properties import ObjectPropertiesMigrator
from wildcard.migrator.workflow import WorkflowStateMigrator
from wildcard.migrator.workflow import WorkflowHistoryMigrator
try:
    from Products.Archetypes.interfaces._base import IBaseObject
except:
    from Products.Archetypes.interfaces.base import IBaseObject
from zope.annotation.interfaces import IAnnotations
from persistent.dict import PersistentDict
from Acquisition import aq_base
from Acquisition import aq_parent
from Acquisition import aq_inner
from zope.dottedname.resolve import resolve
from zope.interface import alsoProvides
from zope.interface import directlyProvidedBy
from Products.CMFEditions.utilities import dereference
from Products.CMFEditions.interfaces.IStorage import StoragePurgeError
from Products.CMFEditions.utilities import wrap
from DateTime import DateTime
from wildcard.migrator import mjson as json
from zope.app.component.hooks import getSite
import re
from Products.CMFPlone.interfaces.siteroot import IPloneSiteRoot
from wildcard.migrator.portlets import PortletsMigrator
from persistent.list import PersistentList
try:
    from Persistence.mapping import PersistentMapping
except:
    from persistent.mapping import PersistentMapping
from BTrees.OOBTree import OOBTree
from plone.app.redirector.interfaces import IRedirectionStorage
from zope.component import queryUtility
from ZODB.POSException import POSKeyError
from wildcard.migrator.utils import safeTraverse


resolveuid_re = re.compile('resolveuid/([a-zA-Z0-9\-]*)\"')
_portal_type_conversions = {
    'Large Plone Folder': 'Folder',
    'Blob': 'File'
}


def getPT(obj):
    pt = aq_base(obj).portal_type
    return _portal_type_conversions.get(pt, pt)


def createObject(parent, _type, id):
    _type = _portal_type_conversions.get(_type, _type)
    pt = getToolByName(parent, 'portal_types')
    type_info = pt.getTypeInfo(_type)
    ob = type_info._constructInstance(parent, id)
    # CMFCore compatibility
    if hasattr(type_info, '_finishConstruction'):
        return type_info._finishConstruction(ob)
    else:
        return ob


class FolderContentsMigrator(BaseMigrator):
    title = "Folder Contents"
    _type = 'folder'

    def get(self):
        values = []
        for id in self.obj.objectIds():
            try:
                o = self.obj[id]
                if IBaseObject.providedBy(o):
                    values.append({
                        'id': id,
                        'portal_type': getPT(o),
                        'modified': o.ModificationDate()
                    })
            except KeyError:
                pass
        return values

    def set(self, values):
        for data in values:
            id = str(data['id'])
            portal_type = str(data['portal_type'])
            if id not in self.obj.objectIds():
                yield createObject(self.obj, portal_type, id)
            else:
                yield self.obj[id]
addMigrator(FolderContentsMigrator)


class SiteContentsMigrator(FolderContentsMigrator):
    title = "Site Contents"
    _type = 'site'

    def __init__(self, site, obj=None):
        self.site = site
        self.obj = site
addMigrator(SiteContentsMigrator)


_skipped_annotations = (
    'plone.folder.ordered.order',  # handled manually
    'plone.folder.ordered.pos',  # handled manually
    'plone.contentrules.localassignments',  # handled through GS
    'plone.locking',
    # let's remove this terrible product
    'vice.outbound.feedconfig.FeedConfigs',
    'htmlpreview'
)


class AnnotationsMigrator(BaseMigrator):
    title = 'Annotations'
    _type = 'object'

    @classmethod
    def _get(kls, obj):
        data = {}
        try:
            annotations = IAnnotations(obj)
        except TypeError:
            return {}
        for key, annotation in annotations.items():
            if key.startswith('Archetypes.storage') or \
                    key in _skipped_annotations or \
                    key.startswith('plone.portlets'):
                # skip because this data should be handled elsewhere
                continue
            data[key] = annotation
        return data

    @classmethod
    def _set(kls, obj, data):
        try:
            annotations = IAnnotations(obj)
        except TypeError:
            return
        for key, annotation in data.items():
            if type(annotation) == dict:
                annotation = PersistentDict(annotation)
            annotations[key] = annotation
addMigrator(AnnotationsMigrator)


class MarkerInterfacesMigrator(BaseMigrator):
    title = 'Marker Interfaces'
    _type = 'object'

    @classmethod
    def _get(kls, obj):
        result = []
        for iface in directlyProvidedBy(aq_base(obj)):
            result.append('%s.%s' % (
                iface.__module__,
                iface.__name__
            ))
        return result

    @classmethod
    def _set(kls, obj, interfaces):
        for iface in interfaces:
            iface = resolve(iface)
            if not iface.providedBy(obj):
                alsoProvides(obj, iface)
addMigrator(MarkerInterfacesMigrator)


class VersionsMigrator(BaseMigrator):
    title = 'Versions'
    _type = 'object'

    @classmethod
    def _get(kls, obj):
        versions = []
        repo_tool = getToolByName(obj, "portal_repository")
        if not repo_tool.isVersionable(obj):
            return []
        history = repo_tool.getHistoryMetadata(obj)
        if not history:
            return []
        length = history.getLength(countPurged=False)
        for i in xrange(length - 1, -1, -1):
            try:
                version = repo_tool.retrieve(obj, i)
                versions.append({
                    'object': ContentObjectMigrator._get(version.object,
                                                        add_versions=False),
                    'sys_metadata': version.sys_metadata
                })
            except POSKeyError:
                pass
        return versions

    @classmethod
    def _set(kls, obj, versions):
        if not versions:
            return

        portal_storage = getToolByName(obj, 'portal_historiesstorage')
        # purge all existing first. Should only be one version though.
        repo_tool = getToolByName(obj, "portal_repository")
        history = repo_tool.getHistoryMetadata(obj)
        if history:
            length = history.getLength(countPurged=False)
            history_id = dereference(obj)
            for i in xrange(length - 1, -1, -1):
                try:
                    portal_storage.purge(history_id, i)
                except StoragePurgeError:
                    pass
        for version in versions:
            kls.saveVersion(obj, version)

    @classmethod
    def saveVersion(kls, obj, version):
        portal_archivist = getToolByName(obj, 'portal_archivist')
        objectdata = version['object']
        sys_metadata = version['sys_metadata']
        metadata = {}
        autoapply = True

        prep = portal_archivist.prepare(obj, metadata, sys_metadata)

        # set the originator of the save operation for the referenced
        # objects
        clone = prep.clone.object
        if sys_metadata['originator'] is None:
            sys_metadata['originator'] = "%s.%s.%s" % (prep.history_id,
                                                       clone.version_id,
                                                       clone.location_id, )
        clone = wrap(clone, aq_parent(aq_inner(obj)))
        ContentObjectMigrator._set(clone, objectdata)  # set obj values...
        # What comes now is the current hardcoded policy:
        #
        # - recursively save inside references, then set a version aware
        #   reference
        # - on outside references only set a version aware reference
        #   (if under version control)
        inside_refs = map(lambda original_refs, clone_refs:
                          (original_refs, clone_refs.getAttribute()),
                          prep.original.inside_refs, prep.clone.inside_refs)
        for orig_ref, clone_ref in inside_refs:
            #self._recursiveSave(orig_ref, app_metadata, sys_metadata,
            #                    autoapply)
            raise
            clone_ref.setReference(orig_ref, remove_info=True)

        outside_refs = map(lambda oref, cref: (oref, cref.getAttribute()),
                           prep.original.outside_refs, prep.clone.outside_refs)
        for orig_ref, clone_ref in outside_refs:
            clone_ref.setReference(orig_ref, remove_info=True)

        portal_archivist.save(prep, autoregister=autoapply)

        # just to ensure that the working copy has the correct
        # ``version_id``
        prep.copyVersionIdFromClone()
addMigrator(VersionsMigrator)


class OwnerMigrator(BaseMigrator):
    title = 'Owner Migrator'
    _type = 'object'

    @classmethod
    def _get(kls, obj):
        return obj.getOwner().getId()

    @classmethod
    def _set(kls, obj, owner):
        if owner != obj.getOwner().getId():
            pm = getToolByName(obj, 'portal_membership')
            member = pm.getMemberById(owner)
            if member:
                user = member.getUser()
                obj.changeOwnership(user, recursive=False)
addMigrator(OwnerMigrator)


class LocalRolesMigrator(BaseMigrator):
    title = 'Local Roles'
    _type = 'object'

    @classmethod
    def _get(kls, obj):
        return obj.get_local_roles()

    @classmethod
    def _set(kls, obj, localroles):
        for principal, roles in localroles:
            obj.manage_setLocalRoles(principal, roles)
addMigrator(LocalRolesMigrator)


class SyndicationMigrator(BaseMigrator):
    title = 'Syndication Information'
    _type = 'object'

    @classmethod
    def _get(kls, obj):
        if 'syndication_information' not in obj.objectIds():
            return {}
        synInfo = obj.syndication_information.aq_base

        return {
            'syUpdatePeriod': getattr(synInfo, 'syUpdatePeriod', 'daily'),
            'syUpdateFrequency': getattr(synInfo, 'syUpdateFrequency', 1),
            'syUpdateBase': getattr(synInfo, 'syUpdateBase', DateTime()),
            'max_items': getattr(synInfo, 'max_items', 15),
            'description': getattr(synInfo, 'description', 'Description'),
        }

    @classmethod
    def _set(self, obj, info):
        if not info:
            return

        if 'syndication_information' not in obj.objectIds():
            portal_syndication = getToolByName(obj, 'portal_syndication')
            portal_syndication.enableSyndication(obj)

        synInfo = obj.syndication_information
        synInfo.syUpdatePeriod = info['syUpdatePeriod']
        synInfo.syUpdateFrequency = info['syUpdateFrequency']
        synInfo.syUpdateBase = info['syUpdateBase']
        synInfo.max_items = info['max_items']
        synInfo.description = info['description']
        synInfo._p_changed = 1
addMigrator(SyndicationMigrator)


def _getUids(value):
    """ must be a string argument"""
    uids = []
    if value.startswith(json._filedata_marker):
        # do not check file data
        return []
    elif value.startswith(json._uid_marker):
        # converted uid
        uids.append(json.decodeUid(value))
    elif 'resolveuid/' in value:
        for match in resolveuid_re.findall(value):
            uids.append(match)
    return uids


def _findUids(data):
    uids = []
    if type(data) in (dict, PersistentDict, PersistentMapping, OOBTree):
        for key, value in data.items():
            if isinstance(value, basestring):
                uids += _getUids(value)
            elif type(value) in (dict, list, tuple, set, PersistentList,
                            PersistentDict, PersistentMapping, OOBTree):
                uids += _findUids(value)
    elif type(data) in (list, tuple, set, PersistentList):
        for value in data:
            if isinstance(value, basestring):
                uids += _getUids(value)
            elif type(value) in (dict, list, tuple, set, PersistentList,
                            PersistentDict, PersistentMapping, OOBTree):
                uids += _findUids(value)
    return uids


def findUids(data):
    uids = _findUids(data)
    uidpaths = []
    uid_cat = getToolByName(getSite(), 'uid_catalog')
    for uid in uids:
        if type(uid) in (list, set, tuple):
            uid, path = uid
        else:
            res = uid_cat(UID=uid)
            if len(res) == 0:
                continue
            path = res[0].getPath()
        uidpaths.append((uid, path))
    return uidpaths


def getParentsData(obj):
    parents = []
    sitepath = '/'.join(getSite().getPhysicalPath())
    obj = aq_parent(aq_inner(obj))
    while not IPloneSiteRoot.providedBy(obj):
        path = '/'.join(obj.getPhysicalPath())[len(sitepath) + 1:]
        pt = aq_base(obj).portal_type
        pt = _portal_type_conversions.get(pt, pt)
        parents.append((path, pt))
        obj = aq_parent(aq_inner(obj))

    return [path for path in reversed(parents)]


class ContentTouchMigrator(BaseMigrator):
    """
    Get information about content in order to
    create stubs or "touch" the content.
    """
    title = "Stub Migrator"
    _type = "_"

    @classmethod
    def _get(kls, obj):
        pt = aq_base(obj).portal_type
        return {
            'id': obj.getId(),
            'parents': getParentsData(obj),
            'portal_type': _portal_type_conversions.get(pt, pt),
            'uid': obj.UID()
        }

    def set(self, data):
        parents = data['parents']
        objid = str(data['id'])
        objparent = self.site
        for path, pt in parents:
            path = str(path)
            id = str(path.split('/')[-1])
            try:
                objparent = objparent[id]
                continue  # if we find it, continue on
            except KeyError:
                pass  # otherwise, create the object
            pt = str(pt)
            objparent = createObject(objparent, pt, id)
        if objid not in objparent.objectIds():
            createObject(objparent, str(data['portal_type']), objid)
        return objparent[objid]
addMigrator(ContentTouchMigrator)


class MultiContentTouchMigrator(BaseMigrator):
    """
    Get information about content in order to
    create stubs or "touch" the content.
    """
    title = "Multi Stub Migrator"
    _type = "_"

    def __init__(self, site, obj=None, totouch=[]):
        super(MultiContentTouchMigrator, self).__init__(site, obj)
        self.totouch = totouch

    def get(self):
        return self._get(self.site, self.totouch)

    @classmethod
    def _get(kls, site, totouch=[]):
        results = []
        for path, uid in totouch:
            path = str(path)
            obj = safeTraverse(site, path.lstrip('/'))
            results.append(ContentTouchMigrator._get(obj))
        return results

    def set(self, data):
        for group in data:
            migr = ContentTouchMigrator(self.site)
            obj = migr.set(group)
            yield obj, group['uid']
addMigrator(MultiContentTouchMigrator)


class RedirectorMigrator(BaseMigrator):
    title = "Redirection"
    _type = 'object'

    @classmethod
    def _get(kls, obj):
        storage = queryUtility(IRedirectionStorage)
        context_path = "/".join(obj.getPhysicalPath())
        site = getSite()
        site_path = '/'.join(site.getPhysicalPath())
        redirects = []
        for redirect in storage.redirects(context_path):
            redirects.append(redirect[len(site_path):])
        return redirects

    @classmethod
    def _set(kls, obj, redirects):
        storage = queryUtility(IRedirectionStorage)
        site = getSite()
        site_path = '/'.join(site.getPhysicalPath())
        context_path = "/".join(obj.getPhysicalPath())
        for redirect in redirects:
            storage.add(site_path + redirect, context_path)
addMigrator(RedirectorMigrator)


class AttributeMissing:
    pass


class AttributeMigrator(BaseMigrator):
    title = 'Attributes'
    _type = 'object'

    _known_attributes_to_copy = [
        '_social_enabled',
        '_adapter_uid'
    ]

    @classmethod
    def _get(kls, obj, attributes=[]):
        attributes.extend(kls._known_attributes_to_copy)
        results = {}
        for attribute in attributes:
            val = getattr(obj, attribute, AttributeMissing)
            if val is not AttributeMissing:
                results[attribute] = val
        return results

    @classmethod
    def _set(kls, obj, values):
        for attribute, value in values.items():
            setattr(obj, attribute, value)


class ContentObjectMigrator(BaseMigrator):
    title = "Migrate Content Item"
    _type = 'object'

    def __init__(self, site, obj=None, attributes=[]):
        super(ContentObjectMigrator, self).__init__(site, obj)
        self.attributes = attributes

    @classmethod
    def _get(kls, obj, add_versions=True, attributes=[]):
        pt = aq_base(obj).portal_type
        data = {
            'fieldvalues': FieldsMigrator._get(obj),
            'id': obj.getId(),
            'portal_type': _portal_type_conversions.get(pt, pt),
            'properties': ObjectPropertiesMigrator._get(obj),
            'workflow': WorkflowStateMigrator._get(obj),
            'workflow_history': WorkflowHistoryMigrator._get(obj),
            'owner': OwnerMigrator._get(obj),
            'annotations': AnnotationsMigrator._get(obj),
            'marker_interfaces': MarkerInterfacesMigrator._get(obj),
            'local_roles': LocalRolesMigrator._get(obj),
            'syndication': SyndicationMigrator._get(obj)
        }
        if add_versions:
            data['versions'] = VersionsMigrator._get(obj)
            data['portlets'] = PortletsMigrator._get(obj)
            data['redirects'] = RedirectorMigrator._get(obj)
            data['uids'] = findUids(data)
            data['attributes'] = AttributeMigrator._get(obj, attributes)
        return data

    def get(self):
        return self._get(self.obj, True, self.attributes)

    @classmethod
    def _set(kls, obj, value):
        FieldsMigrator._set(obj, value.get('fieldvalues', []))
        ObjectPropertiesMigrator._set(obj, value.get('properties', []))
        WorkflowStateMigrator._set(obj, value.get('workflow', ''))
        WorkflowHistoryMigrator._set(obj, value.get('workflow_history', []))
        OwnerMigrator._set(obj, value.get('owner', 'admin'))
        AnnotationsMigrator._set(obj, value.get('annotations', []))
        MarkerInterfacesMigrator._set(obj, value.get('marker_interfaces', []))
        LocalRolesMigrator._set(obj, value.get('local_roles', []))
        VersionsMigrator._set(obj, value.get('versions', []))
        SyndicationMigrator._set(obj, value.get('syndication', {}))
        PortletsMigrator._set(obj, value.get('portlets', None))
        RedirectorMigrator._set(obj, value.get('redirects', []))
        AttributeMigrator._set(obj, value.get('attributes', {}))
        obj._p_changed = 1
addMigrator(ContentObjectMigrator)


class MultiContentObjectMigrator(BaseMigrator):
    """
    Get information about content in order to
    create stubs or "touch" the content.
    """
    title = "multi-Migrate Content Item"
    _type = 'object'

    def __init__(self, site, obj=None, paths=[], attributes=[]):
        super(MultiContentObjectMigrator, self).__init__(site, obj)
        self.attributes = attributes
        self.paths = paths

    def get(self):
        return self._get(self.site, self.paths, self.attributes)

    @classmethod
    def _get(kls, site, paths=[], attributes=[]):
        results = {}
        for path in paths:
            path = str(path).lstrip('/')
            obj = safeTraverse(site, path)
            results[path] = ContentObjectMigrator._get(obj,
                attributes=attributes)
        return results

    def set(self, data):
        raise Exception("do not use...")

    def _set(kls, obj, data):
        raise Exception("do not use...")
addMigrator(MultiContentObjectMigrator)
