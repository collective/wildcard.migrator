
from zope.interface import implements
from zope.interface import providedBy

from zope.component import getUtilitiesFor
from zope.component import queryMultiAdapter
from zope.component import getUtility

from zope.component.interfaces import IFactory
from zope.container.interfaces import INameChooser

from Products.GenericSetup.utils import XMLAdapterBase
from Products.GenericSetup.utils import _getDottedName

from plone.portlets.interfaces import IPortletType
from plone.portlets.interfaces import IPortletManager
from plone.portlets.interfaces import IPortletManagerRenderer
from plone.portlets.interfaces import ILocalPortletAssignmentManager
from plone.portlets.interfaces import IPortletAssignmentMapping
try:
    from plone.portlets.interfaces import IPortletAssignmentSettings
except ImportError:
    IPortletAssignmentSettings = None

from plone.app.portlets.interfaces import IPortletTypeInterface
from plone.app.portlets.utils import assignment_mapping_from_key

from plone.app.portlets.exportimport.interfaces import \
    IPortletAssignmentExportImportHandler

from plone.portlets.constants import USER_CATEGORY
from plone.portlets.constants import GROUP_CATEGORY
from plone.portlets.constants import CONTENT_TYPE_CATEGORY
from plone.portlets.constants import CONTEXT_CATEGORY

from zope.app.component.hooks import getSite
from Products.GenericSetup.utils import PrettyDocument
from wildcard.migrator import BaseMigrator
from wildcard.migrator import addMigrator


def dummyGetId():
    return ''


HAS_BLACKLIST = True
try:
    from Products.GenericSetup.interfaces import IComponentsHandlerBlacklist
except ImportError:
    HAS_BLACKLIST = False

if HAS_BLACKLIST:

    class Blacklist(object):
        implements(IComponentsHandlerBlacklist)

        def getExcludedInterfaces(self):
            return (_getDottedName(IPortletType),
                    _getDottedName(IPortletManager),
                    _getDottedName(IPortletManagerRenderer),
                    )


class PortletsXMLAdapter(XMLAdapterBase):

    name = 'portlets'
    _LOGGER_ID = 'portlets'

    #
    # Main control flow
    #

    def _exportNode(self):
        """Export portlet managers and portlet types
        """
        node = self._doc.createElement('portlets')
        node.appendChild(self._extractPortlets())
        self._logger.info('Portlets exported')
        return node

    def _importNode(self, node):
        """Import portlet managers, portlet types and portlet assignments
        """
        self._initProvider(node)
        self._logger.info('Portlets imported')

    def _initProvider(self, node):
        self._initPortlets(node)

    #
    # Importing
    #

    def _initPortlets(self, node):
        """Actually import portlet data
        """
        for child in node.childNodes:
            # Portlet assignments
            if child.nodeName.lower() == 'assignment':
                self._initAssignmentNode(child)
            # Blacklisting (portlet blocking/unblocking)
            elif child.nodeName.lower() == 'blacklist':
                self._initBlacklistNode(child)

    def _initAssignmentNode(self, node):
        """Create an assignment from a node
        """

        # 1. Determine the assignment mapping and the name
        manager = node.getAttribute('manager')
        category = node.getAttribute('category')
        key = node.getAttribute('key')
        # convert unicode to str as unicode paths are not allowed in
        # restrictedTraverse called in assignment_mapping_from_key
        key = key.encode()

        mapping = assignment_mapping_from_key(self.object, manager,
            category, key, create=True)

        # 2. Either find or create the assignment

        assignment = None
        name = node.getAttribute('name')
        if name:
            assignment = mapping.get(name, None)

        type_ = node.getAttribute('type')

        if assignment is None:
            portlet_factory = getUtility(IFactory, name=type_)
            assignment = portlet_factory()

            if not name:
                chooser = INameChooser(mapping)
                name = chooser.chooseName(None, assignment)

            mapping[name] = assignment

        # aq-wrap it so that complex fields will work
        assignment = assignment.__of__(self.object)

        # set visibility setting
        visible = node.getAttribute('visible')
        if visible and IPortletAssignmentSettings:
            settings = IPortletAssignmentSettings(assignment)
            settings['visible'] = self._convertToBoolean(visible)

        # 3. Use an adapter to update the portlet settings

        portlet_interface = getUtility(IPortletTypeInterface, name=type_)
        assignment_handler = IPortletAssignmentExportImportHandler(assignment)
        assignment_handler.import_assignment(portlet_interface, node)

        # 4. Handle ordering

        insert_before = node.getAttribute('insert-before')
        if insert_before:
            position = None
            keys = list(mapping.keys())

            if insert_before == "*":
                position = 0
            elif insert_before in keys:
                position = keys.index(insert_before)

            if position is not None:
                keys.remove(name)
                keys.insert(position, name)
                mapping.updateOrder(keys)

    def _initBlacklistNode(self, node):
        """Create a blacklisting from a node
        """

        manager = node.getAttribute('manager')
        category = node.getAttribute('category')
        location = str(node.getAttribute('location'))
        status = node.getAttribute('status')

        manager = getUtility(IPortletManager, name=manager)

        if location.startswith('/'):
            location = location[1:]

        item = self.site.unrestrictedTraverse(location, None)
        if item is None:
            return

        assignable = queryMultiAdapter((item, manager),
            ILocalPortletAssignmentManager)

        if status.lower() == 'block':
            assignable.setBlacklistStatus(category, True)
        elif status.lower() == 'show':
            assignable.setBlacklistStatus(category, False)
        elif status.lower() == 'acquire':
            assignable.setBlacklistStatus(category, None)
    #
    # Exporting
    #

    def _extractPortlets(self):
        """Write portlet managers and types to XML
        """
        fragment = self._doc.createDocumentFragment()

        portletSchemata = dict([(iface, name) for name, iface in
                                    getUtilitiesFor(IPortletTypeInterface)])

        def extractMapping(manager_name, category, key, mapping):
            for name, assignment in mapping.items():
                type_ = None
                for schema in providedBy(assignment).flattened():
                    type_ = portletSchemata.get(schema, None)
                    if type_ is not None:
                        break

                if type_ is not None:
                    child = self._doc.createElement('assignment')
                    child.setAttribute('manager', manager_name)
                    child.setAttribute('category', category)
                    child.setAttribute('key', key)
                    child.setAttribute('type', type_)
                    child.setAttribute('name', name)

                    assignment = assignment.__of__(mapping)

                    if IPortletAssignmentSettings:
                        settings = IPortletAssignmentSettings(assignment)
                        visible = settings.get('visible', True)
                        child.setAttribute('visible', repr(visible))

                    handler = IPortletAssignmentExportImportHandler(assignment)
                    handler.export_assignment(schema, self._doc, child)
                    fragment.appendChild(child)

        # Export assignments at the root of the portal (only)
        for manager_name, manager in getUtilitiesFor(IPortletManager):
            mapping = queryMultiAdapter((self.object, manager),
                                        IPortletAssignmentMapping)
            mapping = mapping.__of__(self.object)
            extractMapping(manager_name, CONTEXT_CATEGORY,
                           self.objectpath, mapping)

        # Export blacklistings in the portal root
        for manager_name, manager in getUtilitiesFor(IPortletManager):
            assignable = queryMultiAdapter((self.object, manager),
                                           ILocalPortletAssignmentManager)
            if assignable is None:
                continue
            for category in (USER_CATEGORY, GROUP_CATEGORY,
                             CONTENT_TYPE_CATEGORY, CONTEXT_CATEGORY):
                child = self._doc.createElement('blacklist')
                child.setAttribute('manager', manager_name)
                child.setAttribute('category', category)
                child.setAttribute('location', self.objectpath)

                status = assignable.getBlacklistStatus(category)
                if status == True:
                    child.setAttribute('status', u'block')
                elif status == False:
                    child.setAttribute('status', u'show')
                else:
                    child.setAttribute('status', u'acquire')

                fragment.appendChild(child)

        return fragment
    #
    # Helper methods
    #

    def _checkBasicPortletNodeErrors(self, node, registeredPortletTypes):
        addview = str(node.getAttribute('addview'))
        extend = node.hasAttribute('extend')
        purge = node.hasAttribute('purge')
        exists = addview in registeredPortletTypes

        if extend and purge:
            self._logger.warning('Cannot extend and purge the same ' \
              'portlet type %s!' % addview)
            return True
        if extend and not exists:
            self._logger.warning('Cannot extend portlet type ' \
              '%s because it is not registered.' % addview)
            return True
        if exists and not purge and not extend:
            self._logger.warning('Cannot register portlet type ' \
              '%s because it is already registered.' % addview)
            return True

        return False

    def __init__(self, object):
        self.object = object
        self.site = getSite()
        import logging
        self._logger = logging.getLogger('wildcard.migrator')
        self._doc = PrettyDocument()
        self.sitepath = '/'.join(getSite().getPhysicalPath())
        self.objectpath = '/'.join(
            object.getPhysicalPath())[len(self.sitepath):]


class PortletsMigrator(BaseMigrator):
    """
    Get information about content in order to
    create stubs or "touch" the content.
    """
    title = "Content's Portlet"
    _type = "object"

    @classmethod
    def _get(kls, obj):
        exporter = PortletsXMLAdapter(obj)
        return exporter.body

    @classmethod
    def _set(self, obj, xml):
        if xml:
            exporter = PortletsXMLAdapter(obj)
            exporter.body = xml
addMigrator(PortletsMigrator)