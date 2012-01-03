
from Products.GenericSetup.rolemap import _FILENAME as _ROLEMAP_FILENAME
from Products.GenericSetup.rolemap import RolemapImportConfigurator


def importRolemap( context ):

    """ Import roles / permission map from an XML file.

    o 'context' must implement IImportContext.

    o Register via Python:

      registry = site.setup_tool.setup_steps
      registry.registerStep( 'importRolemap'
                           , '20040518-01'
                           , Products.GenericSetup.rolemap.importRolemap
                           , ()
                           , 'Role / Permission import'
                           , 'Import additional roles, and map '
                           'roles to permissions'
                           )

    o Register via XML:

      <setup-step id="importRolemap"
                  version="20040518-01"
                  handler="Products.GenericSetup.rolemap.importRolemap"
                  title="Role / Permission import"
      >Import additional roles, and map roles to permissions.</setup-step>

    """
    site = context.getSite()
    encoding = context.getEncoding()
    logger = context.getLogger('rolemap')

    text = context.readDataFile( _ROLEMAP_FILENAME )

    if text is not None:

        if context.shouldPurge():

            items = site.__dict__.items()

            for k, v in items:  # XXX: WAAA

                if k == '__ac_roles__':
                    delattr( site, k )

                if k.startswith( '_' ) and k.endswith( '_Permission' ):
                    delattr( site, k )

        rc = RolemapImportConfigurator(site, encoding)
        rolemap_info = rc.parseXML( text )

        immediate_roles = list( getattr(site, '__ac_roles__', []) )
        already = {}

        for role in site.valid_roles():
            already[ role ] = 1

        for role in rolemap_info[ 'roles' ]:

            if already.get( role ) is None:
                immediate_roles.append( role )
                already[ role ] = 1

        immediate_roles.sort()
        site.__ac_roles__ = tuple( immediate_roles )

        for permission in rolemap_info[ 'permissions' ]:
            try:
                site.manage_permission( permission[ 'name' ]
                                  , permission.get('roles', [])
                                  , permission[ 'acquire' ]
                                  )
            except ValueError:
                pass  # do not bother importing invalid ones.

    logger.info('Role / permission map imported.')


from zope.schema.interfaces import IFromUnicode
from zope.schema._bootstrapinterfaces import ConstraintNotSatisfied
from wildcard.migrator.exceptions import MissingObjectException


def from_unicode(self, field, value):
    import zope.schema
    if IFromUnicode.providedBy(field) or isinstance(field, zope.schema.Bool):
        if type(field) == zope.schema.Int and len(value) == 0:
            return None
        try:
            return field.fromUnicode(value)
        except ConstraintNotSatisfied:
            if type(field) == zope.schema.Choice and \
                    zope.schema.interfaces.ISource.providedBy(field.source):
                raise MissingObjectException(value)
            raise
    else:
        return self.field_typecast(field, value)
