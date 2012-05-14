##############################################################################
#
# Copyright (c) 2002 Nexedi SARL and Contributors. All Rights Reserved.
#                    Jean-Paul Smets-Solanes <jp@nexedi.com>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from Products.CMFCore.CatalogTool import CatalogTool as CMFCoreCatalogTool
from Products.ZSQLCatalog.ZSQLCatalog import ZCatalog
from Products.ZSQLCatalog.SQLCatalog import Query, ComplexQuery
from Products.ERP5Type import Permissions
from AccessControl import ClassSecurityInfo, getSecurityManager
from Products.CMFCore.utils import UniqueObject, _getAuthenticatedUser, getToolByName
from Products.ERP5Type.Globals import InitializeClass, DTMLFile
from Acquisition import aq_base, aq_inner, aq_parent, ImplicitAcquisitionWrapper
from Products.CMFActivity.ActiveObject import ActiveObject
from Products.ERP5Type.TransactionalVariable import getTransactionalVariable

from AccessControl.PermissionRole import rolesForPermissionOn

from MethodObject import Method

from Products.ERP5Security import mergedLocalRoles
from Products.ERP5Security.ERP5UserManager import SUPER_USER
from Products.ERP5Type.Utils import sqlquote

import warnings
from zLOG import LOG, PROBLEM, WARNING, INFO

ACQUIRE_PERMISSION_VALUE = []
DYNAMIC_METHOD_NAME = 'z_related_'
DYNAMIC_METHOD_NAME_LEN = len(DYNAMIC_METHOD_NAME)
STRICT_DYNAMIC_METHOD_NAME = DYNAMIC_METHOD_NAME + 'strict_'
STRICT_DYNAMIC_METHOD_NAME_LEN = len(STRICT_DYNAMIC_METHOD_NAME)
RELATED_DYNAMIC_METHOD_NAME = '_related'
# Negative as it's used as a slice end offset
RELATED_DYNAMIC_METHOD_NAME_LEN = -len(RELATED_DYNAMIC_METHOD_NAME)
ZOPE_SECURITY_SUFFIX = '__roles__'

class IndexableObjectWrapper(object):

    def __init__(self, ob):
        self.__ob = ob

    def __getattr__(self, name):
        return getattr(self.__ob, name)

    # We need to update the uid during the cataloging process
    uid = property(lambda self: self.__ob.getUid(),
                   lambda self, value: setattr(self.__ob, 'uid', value))

    def _getSecurityParameterList(self):
      result = self.__dict__.get('_cache_result', None)
      if result is None:
        ob = self.__ob
        # For each group or user, we have a list of roles, this list
        # give in this order : [roles on object, roles acquired on the parent,
        # roles acquired on the parent of the parent....]
        # So if we have ['-Author','Author'] we should remove the role 'Author'
        # but if we have ['Author','-Author'] we have to keep the role 'Author'
        localroles = {}
        skip_role_set = set()
        skip_role = skip_role_set.add
        clear_skip_role = skip_role_set.clear
        for key, role_list in mergedLocalRoles(ob).iteritems():
          new_role_list = []
          new_role = new_role_list.append
          clear_skip_role()
          for role in role_list:
            if role[:1] == '-':
              skip_role(role[1:])
            elif role not in skip_role_set:
              new_role(role)
          if len(new_role_list)>0:
            localroles[key] = new_role_list

        portal = ob.getPortalObject()
        role_dict = dict(portal.portal_catalog.getSQLCatalog().\
                                              getSQLCatalogRoleKeysList())
        getUserById = portal.acl_users.getUserById

        # For each local role of a user:
        #   If the local role grants View permission, add it.
        # Every addition implies 2 lines:
        #   user:<user_id>
        #   user:<user_id>:<role_id>
        # A line must not be present twice in final result.
        allowed = set(rolesForPermissionOn('View', ob))
        # XXX the permission name is included by default for verbose
        # logging of security errors, but the catalog does not need to
        # index it. Unfortunately, rolesForPermissionOn does not have
        # an option to disable this behavior at calling time, so
        # discard it explicitly.
        allowed.discard('_View_Permission')
        # XXX Owner is hardcoded, in order to prevent searching for user on the
        # site root.
        allowed.discard('Owner')
        add = allowed.add
        user_role_dict = {}
        user_view_permission_role_dict = {}
        for user, roles in localroles.iteritems():
          prefix = 'user:' + user
          for role in roles:
            if (role in role_dict) and (getUserById(user) is not None):
              # If role is monovalued, check if key is a user.
              # If not, continue to index it in roles_and_users table.
              user_role_dict[role] = user
              if role in allowed:
                user_view_permission_role_dict[role] = user
            elif role in allowed:
              add(prefix)
              add(prefix + ':' + role)

        self._cache_result = result = (sorted(allowed), user_role_dict,
                                       user_view_permission_role_dict)
      return result

    def allowedRolesAndUsers(self):
      """
      Return a list of roles and users with View permission.
      Used by Portal Catalog to filter out items you're not allowed to see.

      WARNING (XXX): some user base local role association is currently
      being stored (ex. to be determined). This should be prevented or it will
      make the table explode. To analyse the symptoms, look at the
      user_and_roles table. You will find some user:foo values
      which are not necessary.
      """
      return self._getSecurityParameterList()[0]

    def getAssignee(self):
      """Returns the user ID of the user with 'Assignee' local role on this
      document.

      If there is more than one Assignee local role, the result is undefined.
      """
      return self._getSecurityParameterList()[1].get('Assignee', None)

    def getViewPermissionAssignee(self):
      """Returns the user ID of the user with 'Assignee' local role on this
      document, if the Assignee role has View permission.

      If there is more than one Assignee local role, the result is undefined.
      """
      return self._getSecurityParameterList()[2].get('Assignee', None)

    def getViewPermissionAssignor(self):
      """Returns the user ID of the user with 'Assignor' local role on this
      document, if the Assignor role has View permission.

      If there is more than one Assignor local role, the result is undefined.
      """
      return self._getSecurityParameterList()[2].get('Assignor', None)

    def getViewPermissionAssociate(self):
      """Returns the user ID of the user with 'Associate' local role on this
      document, if the Associate role has View permission.

      If there is more than one Associate local role, the result is undefined.
      """
      return self._getSecurityParameterList()[2].get('Associate', None)

    def __repr__(self):
      return '<Products.ERP5Catalog.CatalogTool.IndexableObjectWrapper'\
          ' for %s>' % ('/'.join(self.__ob.getPhysicalPath()), )


class RelatedBaseCategory(Method):
    """A Dynamic Method to act as a related key.
    """
    def __init__(self, id, strict_membership=0, related=0):
      self._id = id
      if strict_membership:
        strict = 'AND %(category_table)s.category_strict_membership = 1\n'
      else:
        strict = ''
      # From the point of view of query_table, we are looking up objects...
      if related:
        # ... which have a relation toward us
        # query_table's uid = category table's category_uid
        query_table_side = 'category_uid'
        # category table's uid = foreign_table's uid
        foreign_side = 'uid'
      else:
        # ... toward which we have a relation
        # query_table's uid = category table's uid
        query_table_side = 'uid'
        # category table's category_uid = foreign_table's uid
        foreign_side = 'category_uid'
      self._template = """\
%%(category_table)s.base_category_uid = %%(base_category_uid)s
%(strict)sAND %%(foreign_catalog)s.uid = %%(category_table)s.%(foreign_side)s
%%(RELATED_QUERY_SEPARATOR)s
%%(category_table)s.%(query_table_side)s = %%(query_table)s.uid""" % {
          'strict': strict,
          'foreign_side': foreign_side,
          'query_table_side': query_table_side,
      }

    def __call__(self, instance, table_0, table_1, query_table='catalog',
        RELATED_QUERY_SEPARATOR=' AND ', **kw):
      """Create the sql code for this related key."""
      # Note: in normal conditions, our category's uid will not change from
      # one invocation to the next.
      return self._template % {
        'base_category_uid': instance.getPortalObject().portal_categories.\
          _getOb(self._id).getUid(),
        'query_table': query_table,
        'category_table': table_0,
        'foreign_catalog': table_1,
        'RELATED_QUERY_SEPARATOR': RELATED_QUERY_SEPARATOR,
      }

class CatalogTool (UniqueObject, ZCatalog, CMFCoreCatalogTool, ActiveObject):
    """
    This is a ZSQLCatalog that filters catalog queries.
    It is based on ZSQLCatalog
    """
    id = 'portal_catalog'
    meta_type = 'ERP5 Catalog'
    security = ClassSecurityInfo()

    default_result_limit = None
    default_count_limit = 1

    manage_options = ({ 'label' : 'Overview', 'action' : 'manage_overview' },
                     ) + ZCatalog.manage_options

    def __init__(self):
        ZCatalog.__init__(self, self.getId())

    # Explicit Inheritance
    __url = CMFCoreCatalogTool.__url
    manage_catalogFind = CMFCoreCatalogTool.manage_catalogFind

    security.declareProtected(Permissions.ManagePortal
                , 'manage_schema')
    manage_schema = DTMLFile('dtml/manageSchema', globals())

    def getPreferredSQLCatalogId(self, id=None):
      """
      Get the SQL Catalog from preference.
      """
      if id is None:
        # Check if we want to use an archive
        #if getattr(aq_base(self.portal_preferences), 'uid', None) is not None:
        archive_path = self.portal_preferences.getPreferredArchive(sql_catalog_id=self.default_sql_catalog_id)
        if archive_path not in ('', None):
          try:
            archive = self.restrictedTraverse(archive_path)
          except KeyError:
            # Do not fail if archive object has been removed,
            # but preference is not up to date
            return None
          if archive is not None:
            catalog_id = archive.getCatalogId()
            if catalog_id not in ('', None):
              return catalog_id
        return None
      else:
        return id

    def _listAllowedRolesAndUsers(self, user):
        # We use ERP5Security PAS based authentication
        try:
          # check for proxy role in stack
          eo = getSecurityManager()._context.stack[-1]
          proxy_roles = getattr(eo, '_proxy_roles',None)
        except IndexError:
          proxy_roles = None
        if proxy_roles:
          # apply proxy roles
          user = eo.getOwner()
          result = list(proxy_roles)
        else:
          result = list(user.getRoles())
        result.append('Anonymous')
        result.append('user:%s' % user.getId())
        # deal with groups
        getGroups = getattr(user, 'getGroups', None)
        if getGroups is not None:
            groups = list(user.getGroups())
            groups.append('role:Anonymous')
            if 'Authenticated' in result:
                groups.append('role:Authenticated')
            for group in groups:
                result.append('user:%s' % group)
        # end groups
        return result

    # Schema Management
    def editColumn(self, column_id, sql_definition, method_id, default_value, REQUEST=None, RESPONSE=None):
      """
        Modifies a schema column of the catalog
      """
      new_schema = []
      for c in self.getIndexList():
        if c.id == index_id:
          new_c = {'id': index_id, 'sql_definition': sql_definition, 'method_id': method_id, 'default_value': default_value}
        else:
          new_c = c
        new_schema.append(new_c)
      self.setColumnList(new_schema)

    def setColumnList(self, column_list):
      """
      """
      self._sql_schema = column_list

    def getColumnList(self):
      """
      """
      if not hasattr(self, '_sql_schema'): self._sql_schema = []
      return self._sql_schema

    def getColumn(self, column_id):
      """
      """
      for c in self.getColumnList():
        if c.id == column_id:
          return c
      return None

    def editIndex(self, index_id, sql_definition, REQUEST=None, RESPONSE=None):
      """
        Modifies the schema of the catalog
      """
      new_index = []
      for c in self.getIndexList():
        if c.id == index_id:
          new_c = {'id': index_id, 'sql_definition': sql_definition}
        else:
          new_c = c
        new_index.append(new_c)
      self.setIndexList(new_index)

    def setIndexList(self, index_list):
      """
      """
      self._sql_index = index_list

    def getIndexList(self):
      """
      """
      if not hasattr(self, '_sql_index'): self._sql_index = []
      return self._sql_index

    def getIndex(self, index_id):
      """
      """
      for c in self.getIndexList():
        if c.id == index_id:
          return c
      return None


    security.declarePublic('getAllowedRolesAndUsers')
    def getAllowedRolesAndUsers(self, sql_catalog_id=None, **kw):
      """
        Return allowed roles and users.

        This is supposed to be used with Z SQL Methods to check permissions
        when you list up documents. It is also able to take into account
        a parameter named local_roles so that listed documents only include
        those documents for which the user (or the group) was
        associated one of the given local roles.

        The use of getAllowedRolesAndUsers is deprecated, you should use
        getSecurityQuery instead
      """
      user = _getAuthenticatedUser(self)
      user_str = str(user)
      user_is_superuser = (user_str == SUPER_USER)
      allowedRolesAndUsers = self._listAllowedRolesAndUsers(user)
      role_column_dict = {}
      local_role_column_dict = {}
      catalog = self.getSQLCatalog(sql_catalog_id)
      column_map = catalog.getColumnMap()

      # We only consider here the Owner role (since it was not indexed)
      # since some objects may only be visible by their owner
      # which was not indexed
      for role, column_id in catalog.getSQLCatalogRoleKeysList():
        # XXX This should be a list
        if not user_is_superuser:
          try:
            # if called by an executable with proxy roles, we don't use
            # owner, but only roles from the proxy.
            eo = getSecurityManager()._context.stack[-1]
            proxy_roles = getattr(eo, '_proxy_roles', None)
            if not proxy_roles:
              role_column_dict[column_id] = user_str
          except IndexError:
            role_column_dict[column_id] = user_str

      # Patch for ERP5 by JP Smets in order
      # to implement worklists and search of local roles
      local_roles = kw.get('local_roles', None)
      if local_roles:
        local_role_dict = dict(catalog.getSQLCatalogLocalRoleKeysList())
        role_dict = dict(catalog.getSQLCatalogRoleKeysList())
        # XXX user is not enough - we should also include groups of the user
        new_allowedRolesAndUsers = []
        new_role_column_dict = {}
        # Turn it into a list if necessary according to ';' separator
        if isinstance(local_roles, str):
          local_roles = local_roles.split(';')
        # Local roles now has precedence (since it comes from a WorkList)
        for user_or_group in allowedRolesAndUsers:
          for role in local_roles:
            # Performance optimisation
            if local_role_dict.has_key(role):
              # XXX This should be a list
              # If a given role exists as a column in the catalog,
              # then it is considered as single valued and indexed
              # through the catalog.
              if not user_is_superuser:
                # XXX This should be a list
                # which also includes all user groups
                column_id = local_role_dict[role]
                local_role_column_dict[column_id] = user_str
            if role_dict.has_key(role):
              # XXX This should be a list
              # If a given role exists as a column in the catalog,
              # then it is considered as single valued and indexed
              # through the catalog.
              if not user_is_superuser:
                # XXX This should be a list
                # which also includes all user groups
                column_id = role_dict[role]
                new_role_column_dict[column_id] = user_str
            new_allowedRolesAndUsers.append('%s:%s' % (user_or_group, role))
        if local_role_column_dict == {}:
          allowedRolesAndUsers = new_allowedRolesAndUsers
          role_column_dict = new_role_column_dict


      return allowedRolesAndUsers, role_column_dict, local_role_column_dict

    def getSecurityUidListAndRoleColumnDict(self, sql_catalog_id=None, **kw):
      """
        Return a list of security Uids and a dictionnary containing available
        role columns.

        XXX: This method always uses default catalog. This should not break a
        site as long as security uids are considered consistent among all
        catalogs.
      """
      allowedRolesAndUsers, role_column_dict, local_role_column_dict = \
          self.getAllowedRolesAndUsers(**kw)
      catalog = self.getSQLCatalog(sql_catalog_id)
      method = getattr(catalog, catalog.sql_search_security, None)
      if allowedRolesAndUsers:
        allowedRolesAndUsers.sort()
        cache_key = tuple(allowedRolesAndUsers)
        tv = getTransactionalVariable()
        try:
          security_uid_cache = tv['getSecurityUidListAndRoleColumnDict']
        except KeyError:
          security_uid_cache = tv['getSecurityUidListAndRoleColumnDict'] = {}
        try:
          security_uid_list = security_uid_cache[cache_key]
        except KeyError:
          if method is None:
            warnings.warn("The usage of allowedRolesAndUsers is "\
                          "deprecated. Please update your catalog "\
                          "business template.", DeprecationWarning)
            security_uid_list = [x.security_uid for x in \
              self.unrestrictedSearchResults(
                allowedRolesAndUsers=allowedRolesAndUsers,
                select_expression="security_uid",
                group_by_expression="security_uid")]
          else:
            # XXX: What with this string transformation ?! Souldn't it be done in
            # dtml instead ?
            allowedRolesAndUsers = [sqlquote(role) for role in allowedRolesAndUsers]
            security_uid_list = [x.uid for x in method(security_roles_list = allowedRolesAndUsers)]
          security_uid_cache[cache_key] = security_uid_list
      else:
        security_uid_list = []
      return security_uid_list, role_column_dict, local_role_column_dict

    security.declarePublic('getSecurityQuery')
    def getSecurityQuery(self, query=None, sql_catalog_id=None, **kw):
      """
        Build a query based on allowed roles or on a list of security_uid
        values. The query takes into account the fact that some roles are
        catalogued with columns.
      """
      original_query = query
      security_uid_list, role_column_dict, local_role_column_dict = \
          self.getSecurityUidListAndRoleColumnDict(
              sql_catalog_id=sql_catalog_id, **kw)
      if role_column_dict:
        query_list = []
        for key, value in role_column_dict.items():
          new_query = Query(**{key : value})
          query_list.append(new_query)
        operator_kw = {'operator': 'OR'}
        query = ComplexQuery(*query_list, **operator_kw)
        # If security_uid_list is empty, adding it to criterions will only
        # result in "false or [...]", so avoid useless overhead by not
        # adding it at all.
        if security_uid_list:
          query = ComplexQuery(Query(security_uid=security_uid_list, operator='IN'),
                               query, operator='OR')
      elif security_uid_list:
        query = Query(security_uid=security_uid_list, operator='IN')
      else:
        # XXX A false query has to be generated.
        # As it is not possible to use SQLKey for now, pass impossible value
        # on uid (which will be detected as False by MySQL, as it is not in the
        # column range)
        # Do not pass security_uid_list as empty in order to prevent useless
        # overhead
        query = Query(uid=-1)

      if local_role_column_dict:
        query_list = []
        for key, value in local_role_column_dict.items():
          new_query = Query(**{key : value})
          query_list.append(new_query)
        operator_kw = {'operator': 'AND'}
        local_role_query = ComplexQuery(*query_list, **operator_kw)
        query = ComplexQuery(query, local_role_query, operator='AND')

      if original_query is not None:
        query = ComplexQuery(query, original_query, operator='AND')
      return query

    # searchResults has inherited security assertions.
    def searchResults(self, query=None, **kw):
        """
        Calls ZCatalog.searchResults with extra arguments that
        limit the results to what the user is allowed to see.
        """
        #if not _checkPermission(
        #    Permissions.AccessInactivePortalContent, self):
        #    now = DateTime()
        #    kw[ 'effective' ] = { 'query' : now, 'range' : 'max' }
        #    kw[ 'expires'   ] = { 'query' : now, 'range' : 'min' }

        catalog_id = self.getPreferredSQLCatalogId(kw.pop("sql_catalog_id", None))
        query = self.getSecurityQuery(query=query, sql_catalog_id=catalog_id, **kw)
        kw.setdefault('limit', self.default_result_limit)
        # get catalog from preference
        #LOG("searchResult", INFO, catalog_id)
        #         LOG("searchResult", INFO, ZCatalog.searchResults(self, query=query, sql_catalog_id=catalog_id, src__=1, **kw))
        return ZCatalog.searchResults(self, query=query, sql_catalog_id=catalog_id, **kw)

    __call__ = searchResults

    security.declarePrivate('unrestrictedSearchResults')
    def unrestrictedSearchResults(self, REQUEST=None, **kw):
        """Calls ZSQLCatalog.searchResults directly without restrictions.
        """
        kw.setdefault('limit', self.default_result_limit)
        return ZCatalog.searchResults(self, REQUEST, **kw)

    # We use a string for permissions here due to circular reference in import
    # from ERP5Type.Permissions
    security.declareProtected('Search ZCatalog', 'getResultValue')
    def getResultValue(self, query=None, **kw):
        """
        A method to factor common code used to search a single
        object in the database.
        """
        kw.setdefault('limit', 1)
        result = self.searchResults(query=query, **kw)
        try:
          return result[0].getObject()
        except IndexError:
          return None

    security.declarePrivate('unrestrictedGetResultValue')
    def unrestrictedGetResultValue(self, query=None, **kw):
        """
        A method to factor common code used to search a single
        object in the database. Same as getResultValue but without
        taking into account security.
        """
        kw.setdefault('limit', 1)
        result = self.unrestrictedSearchResults(query=query, **kw)
        try:
          return result[0].getObject()
        except IndexError:
          return None

    def countResults(self, query=None, **kw):
        """
            Calls ZCatalog.countResults with extra arguments that
            limit the results to what the user is allowed to see.
        """
        # XXX This needs to be set again
        #if not _checkPermission(
        #    Permissions.AccessInactivePortalContent, self):
        #    base = aq_base(self)
        #    now = DateTime()
        #    #kw[ 'effective' ] = { 'query' : now, 'range' : 'max' }
        #    #kw[ 'expires'   ] = { 'query' : now, 'range' : 'min' }
        catalog_id = self.getPreferredSQLCatalogId(kw.pop("sql_catalog_id", None))
        query = self.getSecurityQuery(query=query, sql_catalog_id=catalog_id, **kw)
        kw.setdefault('limit', self.default_count_limit)
        # get catalog from preference
        return ZCatalog.countResults(self, query=query, sql_catalog_id=catalog_id, **kw)

    security.declarePrivate('unrestrictedCountResults')
    def unrestrictedCountResults(self, REQUEST=None, **kw):
        """Calls ZSQLCatalog.countResults directly without restrictions.
        """
        return ZCatalog.countResults(self, REQUEST, **kw)

    def wrapObject(self, object, sql_catalog_id=None, **kw):
        """
          Return a wrapped object for reindexing.
        """
        catalog = self.getSQLCatalog(sql_catalog_id)
        if catalog is None:
          # Nothing to do.
          LOG('wrapObject', 0, 'Warning: catalog is not available')
          return (None, None)

        document_object = aq_inner(object)
        w = IndexableObjectWrapper(document_object)

        wf = getToolByName(self, 'portal_workflow')
        if wf is not None:
          w.__dict__.update(wf.getCatalogVariablesFor(object))

        # Find the parent definition for security
        is_acquired = 0
        while getattr(document_object, 'isRADContent', 0):
          # This condition tells which object should acquire
          # from their parent.
          # XXX Hardcode _View_Permission for a performance point of view
          if getattr(aq_base(document_object), '_View_Permission', ACQUIRE_PERMISSION_VALUE) == ACQUIRE_PERMISSION_VALUE\
             and document_object._getAcquireLocalRoles():
            document_object = document_object.aq_parent
            is_acquired = 1
          else:
            break
        if is_acquired:
          document_w = IndexableObjectWrapper(document_object)
        else:
          document_w = w

        (security_uid, optimised_roles_and_users) = catalog.getSecurityUid(document_w)
        #LOG('catalog_object optimised_roles_and_users', 0, str(optimised_roles_and_users))
        # XXX we should build vars begore building the wrapper
        w.optimised_roles_and_users = optimised_roles_and_users
        predicate_property_dict = catalog.getPredicatePropertyDict(object)
        if predicate_property_dict is not None:
          w.predicate_property_dict = predicate_property_dict
        else:
          w.predicate_property_dict = {}
        w.security_uid = security_uid
        (subject_set_uid, optimised_subject_list) = catalog.getSubjectSetUid(document_w)
        w.optimised_subject_list = optimised_subject_list
        w.subject_set_uid = subject_set_uid

        return ImplicitAcquisitionWrapper(w, aq_parent(document_object))

    security.declarePrivate('reindexObject')
    def reindexObject(self, object, idxs=None, sql_catalog_id=None,**kw):
        '''Update catalog after object data has changed.
        The optional idxs argument is a list of specific indexes
        to update (all of them by default).
        '''
        if idxs is None: idxs = []
        url = self.__url(object)
        self.catalog_object(object, url, idxs=idxs, sql_catalog_id=sql_catalog_id,**kw)


    def catalogObjectList(self, object_list, *args, **kw):
        """Catalog a list of objects"""
        m = object_list[0]
        if type(m) is list:
          tmp_object_list = [x[0] for x in object_list]
          super(CatalogTool, self).catalogObjectList(tmp_object_list, **m[2])
          if tmp_object_list:
            for x in object_list:
              if x[0] in tmp_object_list:
                del object_list[3] # no result means failed
        else:
          super(CatalogTool, self).catalogObjectList(object_list, *args, **kw)

    security.declarePrivate('uncatalogObjectList')
    def uncatalogObjectList(self, message_list):
      """Uncatalog a list of objects"""
      # XXX: this is currently only a placeholder for further optimization
      #      (for the moment, it's not faster than the dummy group method)
      for m in message_list:
        self.unindexObject(*m[1], **m[2])

    security.declarePrivate('unindexObject')
    def unindexObject(self, object=None, path=None, uid=None,sql_catalog_id=None):
        """
          Remove from catalog.
        """
        if path is None and uid is None:
          if object is None:
            raise TypeError, 'One of uid, path and object parameters must not be None'
          path = self.__url(object)
        if uid is None:
          raise TypeError, "unindexObject supports only uid now"
        self.uncatalog_object(path=path, uid=uid, sql_catalog_id=sql_catalog_id)

    security.declarePrivate('beforeUnindexObject')
    def beforeUnindexObject(self, object, path=None, uid=None,sql_catalog_id=None):
        """
          Remove from catalog.
        """
        if path is None and uid is None:
          path = self.__url(object)
        self.beforeUncatalogObject(path=path,uid=uid, sql_catalog_id=sql_catalog_id)

    security.declarePrivate('getUrl')
    def getUrl(self, object):
      return self.__url(object)

    security.declarePrivate('moveObject')
    def moveObject(self, object, idxs=None):
        """
          Reindex in catalog, taking into account
          peculiarities of ERP5Catalog / ZSQLCatalog

          Useless ??? XXX
        """
        if idxs is None: idxs = []
        url = self.__url(object)
        self.catalog_object(object, url, idxs=idxs, is_object_moved=1)

    security.declarePublic('getPredicatePropertyDict')
    def getPredicatePropertyDict(self, object):
      """
      Construct a dictionnary with a list of properties
      to catalog into the table predicate
      """
      if not object.providesIPredicate():
        return None
      object = object.asPredicate()
      if object is None:
        return None
      property_dict = {}
      identity_criterion = getattr(object,'_identity_criterion',None)
      range_criterion = getattr(object,'_range_criterion',None)
      if identity_criterion is not None:
        for property, value in identity_criterion.items():
          if value is not None:
            property_dict[property] = value
      if range_criterion is not None:
        for property, (min, max) in range_criterion.items():
          if min is not None:
            property_dict['%s_range_min' % property] = min
          if max is not None:
            property_dict['%s_range_max' % property] = max
      property_dict['membership_criterion_category_list'] = object.getMembershipCriterionCategoryList()
      return property_dict

    security.declarePrivate('getDynamicRelatedKeyList')
    def getDynamicRelatedKeyList(self, key_list, sql_catalog_id=None):
      """
      Return the list of dynamic related keys.
      This method will try to automatically generate new related key
      by looking at the category tree.

      For exemple it will generate:
      destination_title | category,catalog/title/z_related_destination
      default_destination_title | category,catalog/title/z_related_destination
      strict_destination_title | category,catalog/title/z_related_strict_destination

      strict_ related keys only returns documents which are strictly member of
      the category.
      """
      related_key_list = []
      base_cat_id_list = self.portal_categories.getBaseCategoryDict()
      default_string = 'default_'
      strict_string = 'strict_'
      for key in key_list:
        prefix = ''
        strict = 0
        if key.startswith(default_string):
          key = key[len(default_string):]
          prefix = default_string
        if key.startswith(strict_string):
          strict = 1
          key = key[len(strict_string):]
          prefix = prefix + strict_string
        splitted_key = key.split('_')
        # look from the end of the key from the beginning if we
        # can find 'title', or 'portal_type'...
        for i in range(1,len(splitted_key))[::-1]:
          expected_base_cat_id = '_'.join(splitted_key[0:i])
          if expected_base_cat_id != 'parent' and \
             expected_base_cat_id in base_cat_id_list:
            # We have found a base_category
            end_key = '_'.join(splitted_key[i:])

            if end_key.startswith('related_'):
              end_key = end_key[len('related_'):]
              suffix = '_related'
            else:
              suffix = ''
            # accept only some catalog columns
            if end_key in ('title', 'uid', 'description', 'reference',
                           'relative_url', 'id', 'portal_type',
                           'simulation_state'):
              if strict:
                pattern = '%s%s | category,catalog/%s/z_related_strict_%s%s'
              else:
                pattern = '%s%s | category,catalog/%s/z_related_%s%s'
              related_key_list.append(pattern %
                (prefix, key, end_key, expected_base_cat_id, suffix))

      return related_key_list

    def _aq_dynamic(self, name):
      """
      Automatic related key generation.
      Will generate z_related_[base_category_id] if possible
      """
      result = None
      if name.startswith(DYNAMIC_METHOD_NAME) and \
          not name.endswith(ZOPE_SECURITY_SUFFIX):
        kw = {}
        if name.endswith(RELATED_DYNAMIC_METHOD_NAME):
          end_offset = RELATED_DYNAMIC_METHOD_NAME_LEN
          kw['related'] = 1
        else:
          end_offset = None
        if name.startswith(STRICT_DYNAMIC_METHOD_NAME):
          start_offset = STRICT_DYNAMIC_METHOD_NAME_LEN
          kw['strict_membership'] = 1
        else:
          start_offset = DYNAMIC_METHOD_NAME_LEN
        method = RelatedBaseCategory(name[start_offset:end_offset], **kw)
        setattr(self.__class__, name, method)
        # This getattr has 2 purposes:
        # - wrap in acquisition context
        #   This alone should be explicitly done rather than through getattr.
        # - wrap (if needed) class attribute on the instance
        #   (for the sake of not relying on current implementation details
        #   "too much")
        result = getattr(self, name)
      return result

    def _searchAndActivate(self, method_id, method_args=(), method_kw={},
                           activate_kw={}, min_uid=None, **kw):
      """Search the catalog and run a script by activity on all found objects

      This method is configurable (via 'packet_size' & 'activity_count'
      parameters) so that it can work efficiently with databases of any size.

      'activate_kw' may specify an active process to collect results.
      """
      catalog_kw = dict(kw)
      packet_size = catalog_kw.pop('packet_size', 30)
      limit = packet_size * catalog_kw.pop('activity_count', 100)
      if min_uid:
        catalog_kw['uid'] = {'query': min_uid, 'range': 'nlt'}
      if catalog_kw.pop('restricted', False):
        search = self
      else:
        search = self.unrestrictedSearchResults
      r = search(sort_on=(('uid','ascending'),), limit=limit, **catalog_kw)
      result_count = len(r)
      if result_count:
        if result_count == limit:
          next_kw = dict(activate_kw, priority=1+activate_kw.get('priority', 1))
          self.activate(activity='SQLQueue', **next_kw) \
              ._searchAndActivate(method_id,method_args, method_kw,
                                  activate_kw, r[-1].getUid(), **kw)
        r = [x.getPath() for x in r]
        r.sort()
        activate = self.getPortalObject().portal_activities.activate
        for i in xrange(0, result_count, packet_size):
          activate(activity='SQLQueue', **activate_kw).callMethodOnObjectList(
            r[i:i+packet_size], method_id, *method_args, **method_kw)

    security.declarePublic('searchAndActivate')
    def searchAndActivate(self, *args, **kw):
      """Restricted version of _searchAndActivate"""
      return self._searchAndActivate(restricted=True, *args, **kw)

InitializeClass(CatalogTool)
