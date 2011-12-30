from zope.interface import implements
from wildcard.migrator import BaseMigrator
from wildcard.migrator import addMigrator
from Products.GenericSetup.interfaces import IExportContext
from Products.GenericSetup.interfaces import IImportContext
from zope.app.component.hooks import getSite

from Products.CMFCore.exportimport.properties import importSiteProperties
from Products.CMFCore.exportimport.properties import exportSiteProperties
from Products.CMFPlone.exportimport.propertiestool import exportPloneProperties
from Products.CMFPlone.exportimport.propertiestool import importPloneProperties
from Products.CMFCore.exportimport.typeinfo import exportTypesTool
from Products.CMFCore.exportimport.typeinfo import importTypesTool
from Products.TinyMCE.exportimport import exportTinyMCESettings
from Products.TinyMCE.exportimport import importTinyMCESettings
from Products.ATContentTypes.exportimport.atcttool import exportATCTTool
from Products.ATContentTypes.exportimport.atcttool import importATCTTool
from Products.CMFCore.exportimport.actions import exportActionProviders
from Products.CMFCore.exportimport.actions import importActionProviders
from Products.CMFCore.exportimport.skins import exportSkinsTool
from Products.CMFCore.exportimport.skins import importSkinsTool
from plone.app.registry.exportimport.handler import exportRegistry
from plone.app.registry.exportimport.handler import importRegistry
from plone.app.portlets.exportimport.portlets import exportPortlets
from plone.app.portlets.exportimport.portlets import importPortlets
from Products.ResourceRegistries.exportimport.cssregistry import \
    exportCSSRegistry
from Products.ResourceRegistries.exportimport.cssregistry import \
    importCSSRegistry
from Products.CMFCore.exportimport.catalog import exportCatalogTool
from Products.CMFCore.exportimport.catalog import importCatalogTool
from plone.app.contentrules.exportimport.rules import exportRules
from plone.app.contentrules.exportimport.rules import importRules
from Products.CMFDiffTool.exportimport.difftool import exportDiffTool
from Products.CMFDiffTool.exportimport.difftool import importDiffTool
from Products.CMFCore.exportimport.workflow import exportWorkflowTool
from Products.CMFCore.exportimport.workflow import importWorkflowTool
from Products.ResourceRegistries.exportimport.kssregistry import \
    exportKSSRegistry
from Products.ResourceRegistries.exportimport.kssregistry import \
    importKSSRegistry
from Products.Archetypes.exportimport.archetypetool import exportArchetypeTool
from Products.Archetypes.exportimport.archetypetool import importArchetypeTool
from plone.app.viewletmanager.exportimport.storage import \
    exportViewletSettingsStorage
from plone.app.viewletmanager.exportimport.storage import \
    importViewletSettingsStorage
from Products.CMFCore.exportimport.mailhost import exportMailHost
from Products.CMFCore.exportimport.mailhost import importMailHost
from Products.GenericSetup.rolemap import exportRolemap
from wildcard.migrator.monkey import importRolemap
from Products.ResourceRegistries.exportimport.jsregistry import \
    exportJSRegistry
from Products.ResourceRegistries.exportimport.jsregistry import \
    importJSRegistry
from wildcard.importexport.users import importUsers
from wildcard.importexport.users import exportUsers
from wildcard.importexport.groups import importGroups
from wildcard.importexport.groups import exportGroups
from wildcard.importexport.roles import importRoleAssignments
from wildcard.importexport.roles import exportRoleAssignments

import logging
logger = logging.getLogger('wildcard.migrator')


class BaseFakeContext(object):
    i18n_domain = 'plone'
    shouldPurge = lambda x: True

    def getSite(self, *args, **kwargs):
        return getSite()

    def getLogger(self, *args, **kwargs):
        return logger

    def getEncoding(self):
        return 'utf-8'


class FakeImportContext(BaseFakeContext):
    implements(IImportContext)

    def __init__(self, data={}):
        self.data = data

    def readDataFile(self, filename, subdir=None):
        if subdir is not None:
            filename = '/'.join((subdir, filename))
        if filename in self.data:
            return self.data[filename]
        else:
            return None


class FakeExportContext(BaseFakeContext):
    implements(IExportContext)

    def __init__(self):
        self.data = {}
        self.mime_type = ''

    def writeDataFile(self, filename, text, content_type, subdir=None):
        if subdir is not None:
            filename = '/'.join((subdir, filename))
        self.data[filename] = text
        self.mime_type = content_type


class GSMigrator(BaseMigrator):

    # XXX do it this silly way
    # because if you try and set it directly
    # on the class definition it tries to make
    # the function an instance method
    funcs = {
        'import': None,
        'export': None
    }
    _type = 'gs'

    def get(self):
        exportcontext = FakeExportContext()
        self.funcs['export'](exportcontext)
        return exportcontext.data

    def set(self, data):
        self.funcs['import'](FakeImportContext(data))


class SiteSettings(BaseMigrator):
    title = 'Site Settings'
    _type = 'site'

    def get(self):
        from wildcard.migrator import getMigratorsOfType
        data = {}
        for migrator in getMigratorsOfType('gs'):
            migrator = migrator(self.site, self.obj)
            data[migrator.title] = migrator.get()
        return data

    def set(self, data):
        from wildcard.migrator import getMigratorsOfType
        for migrator in getMigratorsOfType('gs'):
            migrator = migrator(self.site, self.obj)
            migrator.set(data[migrator.title])
addMigrator(SiteSettings)


def GSMigratorGenerator(title, _import, _export):
    class Migrator(GSMigrator):
        pass
    Migrator.title = title
    Migrator.funcs = {
        'import': _import,
        'export': _export
    }
    return Migrator


SitePropertiesMigrator = GSMigratorGenerator(
    'Site Properties', importSiteProperties, exportSiteProperties)
addMigrator(SitePropertiesMigrator)

PortalPropertiesMigrator = GSMigratorGenerator(
    'Portal Properties', importPloneProperties, exportPloneProperties)
addMigrator(PortalPropertiesMigrator)

TypesMigrator = GSMigratorGenerator(
    'Type Tool', importTypesTool, exportTypesTool)
addMigrator(TypesMigrator)

TinyMCEMigrator = GSMigratorGenerator(
    'Tiny MCE', importTinyMCESettings, exportTinyMCESettings)
addMigrator(TinyMCEMigrator)

ATContentTypesMigrator = GSMigratorGenerator(
    'ATCT', importATCTTool, exportATCTTool)
addMigrator(ATContentTypesMigrator)

ActionProvidersMigrator = GSMigratorGenerator(
    'Action Providers', importActionProviders, exportActionProviders)
addMigrator(ActionProvidersMigrator)

SkinsMigrator = GSMigratorGenerator(
    'Skins', importSkinsTool, exportSkinsTool)
addMigrator(SkinsMigrator)

RegistryMigrator = GSMigratorGenerator(
    'Registry', importRegistry, exportRegistry)
addMigrator(RegistryMigrator)

PortletsMigrator = GSMigratorGenerator(
    'Portlets', importPortlets, exportPortlets)
addMigrator(PortletsMigrator)

CSSMigrator = GSMigratorGenerator(
    'CSS', importCSSRegistry, exportCSSRegistry)
addMigrator(CSSMigrator)

RulesMigrator = GSMigratorGenerator(
    'Rules', importRules, exportRules)
addMigrator(RulesMigrator)

CatalogMigrator = GSMigratorGenerator(
    'Catalog', importCatalogTool, exportCatalogTool)
addMigrator(CatalogMigrator)

DiffMigrator = GSMigratorGenerator(
    'Diff', importDiffTool, exportDiffTool)
addMigrator(DiffMigrator)

WorkflowMigrator = GSMigratorGenerator(
    'Workflow', importWorkflowTool, exportWorkflowTool)
addMigrator(WorkflowMigrator)

KSSMigrator = GSMigratorGenerator(
    'KSS', importKSSRegistry, exportKSSRegistry)
addMigrator(KSSMigrator)

ArchetypesMigrator = GSMigratorGenerator(
    'Archetypes', importArchetypeTool, exportArchetypeTool)
addMigrator(ArchetypesMigrator)

ViewletsMigrator = GSMigratorGenerator(
    'Viewlets', importViewletSettingsStorage, exportViewletSettingsStorage)
addMigrator(ViewletsMigrator)

MailHostMigrator = GSMigratorGenerator(
    'Mail Host', importMailHost, exportMailHost)
addMigrator(MailHostMigrator)

RoleMapMigrator = GSMigratorGenerator(
    'RoleMap', importRolemap, exportRolemap)
addMigrator(RoleMapMigrator)

JSMigrator = GSMigratorGenerator(
    'JS', importJSRegistry, exportJSRegistry)
addMigrator(JSMigrator)

GroupsMigrator = GSMigratorGenerator(
    'Groups', importGroups, exportGroups)
addMigrator(GroupsMigrator)

UsersMigrator = GSMigratorGenerator(
    'Users', importUsers, exportUsers)
addMigrator(UsersMigrator)

RolesMigrator = GSMigratorGenerator(
    'Roles', importRoleAssignments, exportRoleAssignments)
addMigrator(RolesMigrator)
