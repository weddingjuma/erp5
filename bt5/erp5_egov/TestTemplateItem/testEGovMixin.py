##############################################################################
#
# Copyright (c) 2008 Nexedi SARL and Contributors. All Rights Reserved.
#                  Fabien Morin <fabien@nexedi.com>
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
##############################################################################
from Testing.ZopeTestCase.PortalTestCase import PortalTestCase
from Products.ERP5Type.tests.ERP5TypeTestCase import ERP5TypeTestCase
from Products.ERP5Type.tests.SecurityTestCase import SecurityTestCase
from AccessControl.SecurityManagement import getSecurityManager
from AccessControl import Unauthorized
from Testing import ZopeTestCase

class TestEGovMixin(SecurityTestCase):
  """Usefull methods for eGov Unit Tests."""
  
  # define all username corresponding to all roles used in eGov
  assignor_login = 'chef'
  assignee_login = 'agent'
  assignee_login_2 = 'agent_2'
  associate_login = 'agent_requested'

  organisation_1_login = 'societe_a'
  organisation_2_login = 'societe_b'

  all_username_list = ( assignor_login,
                        assignee_login,
                        assignee_login_2,
                        #associate_login,
                        organisation_1_login,
                        organisation_2_login)

  all_role_list = ( 'Manager',
                    'Assignor',
                    'Assignee',
                    'Author',
                    'Associate',
                    'Auditor',)

  #Permissions
  VIEW = 'View'
  ACCESS = 'Access contents information'
  ADD = 'Add portal content'
  MODIFY = 'Modify portal content'
  DELETE = 'Delete objects'

  def getBusinessTemplateList(self):
    """return list of business templates to be installed. """
    return ( 'erp5_base',)

  def afterSetUp(self):
    """
      Method called before the launch of the test to initialize some data
    """
    self.createManagerAndLogin()
    # remove all message in the message_table because
    # the previous test might have failed
    message_list = self.getPortal().portal_activities.getMessageList()
    for message in message_list:
      self.getPortal().portal_activities.manageCancel(message.object_path,
                                                      message.method_id)
    self.createUsers()
    self.createOrganisations()
    self.setUpEGovPas()

    # XXX quick hack not to have mysql database pre-fill.
    self.portal.__class__.DeclarationTVA_zGetSIGTASInformation \
        = lambda x,**kw: []

    get_transaction().commit()
    self.tic()
    
  def beforeTearDown(self):
    """Clean up."""
    for module in self.portal.objectValues(spec=('ERP5 Folder',)):
      # we want to keep some IDs
      module.manage_delObjects([x for x in module.objectIds()
                                if x not in ('EUR',)])
    get_transaction().commit()
    self.tic()

  def getUserFolder(self) :
    return getattr(self.getPortal(), 'acl_users', None)

  loginAsUser = PortalTestCase.login

  diff_list = lambda self,x,y: [i for i in x if i not in y] 

  def createManagerAndLogin(self):
    """
      Create a simple user in user_folder with manager rights.
      This user will be used to initialize data in the method afterSetup
    """
    self.getUserFolder()._doAddUser('manager', 'manager', self.all_role_list, 
                                    [])
    self.login('manager')
  
  def createOneUser(self, username, function=None, group=None):
     """Create one person that will be users."""
     person_module = self.getPersonModule()
     user = person_module.newContent(
                              portal_type='Person',
                              reference=username,
                              title=username,
                              id=username,
                              password='secret')
     assignment = user.newContent(portal_type='Assignment')
     if function is not None:
       assignment.setFunction(function)
       self.assertNotEqual(assignment.getFunctionValue(), None)
     if group is not None:
       assignment.setGroup(group)
       self.assertNotEqual(assignment.getGroupValue(), None)
     assignment.open()

  def createUsers(self):
    """Create persons that will be users."""
    module = self.getPersonModule()
    if len(module.getObjectIds()) == 0:
      # create users
      self.createOneUser(self.assignor_login, 'function/section/chef', 
          'group/dgid/di/cge')
      self.createOneUser(self.assignee_login, 'function/impots/inspecteur', 
          'group/dgid/di/cge')
      self.createOneUser(self.assignee_login_2, 'function/impots/inspecteur', 
          'group/dgid/di/cge')
      self.createOneUser(self.associate_login, 'function/section/chef', 
          'group/dgid/di/csf/bf')

      # make this available to catalog
      get_transaction().commit()
      self.tic()

  def createOneOrganisation(self, username, role=None, function=None, 
                            group=None):
    """Create one organisation that will be user."""
    organisation_module = self.getOrganisationModule()
    user = organisation_module.newContent(
                             portal_type='Organisation',
                             title=username,
                             id=username,
                             reference=username,
                             password='secret')
    user.setRole(role)
    user.setFunction(function)
    user.setGroup(group)

    self.assertEqual(user.getRole(), role)
    self.assertEqual(user.getFunction(), function)
    self.assertEqual(user.getGroup(), group)
    self.assertEqual(user.getReference(), username)
  
  def createOrganisations(self):
    """Create organisations that will be users."""
    module = self.getOrganisationModule()
    if len(module.getObjectIds()) == 0:
      self.createOneOrganisation(self.organisation_1_login, 
          role='entreprise/siege')
      self.createOneOrganisation(self.organisation_2_login, 
          role='entreprise/siege')

      # make this available to catalog
      get_transaction().commit()
      self.tic()

  def setUpEGovPas(self):
    '''use safi PAS to be able to login organisation'''
    from Products import ERP5Security
    from Products import PluggableAuthService

    portal = self.getPortalObject()
    acl_users = self.getUserFolder()

    # Add SAFIUserManager
    ZopeTestCase.installProduct('SAFISecurity')
    erp5security_dispatcher = acl_users.manage_addProduct['SAFISecurity']
    # don't add it if it's already here
    if {'meta_type': 'SAFI User Manager', 'id': 'safi_users'} not in \
        erp5security_dispatcher._d._objects:
      erp5security_dispatcher.addSAFIUserManager('safi_users')
    if {'meta_type': 'SAFI Group Manager', 'id': 'safi_groups'} not in \
        erp5security_dispatcher._d._objects :
      erp5security_dispatcher.addSAFIGroupManager('safi_groups')
    # Register ERP5UserManager Interface
    acl_users.safi_users.manage_activateInterfaces(('IAuthenticationPlugin',
                                                    'IUserEnumerationPlugin',))
    acl_users.safi_groups.manage_activateInterfaces(('IGroupsPlugin',))

    # desactivate the erp5 plugin
    plugins = acl_users.safi_groups.plugins
    interface = plugins._getInterfaceFromName('IGroupsPlugin')
    if 'erp5_groups' in list(plugins._getPlugins(interface)):
      plugins.deactivatePlugin( interface, 'erp5_groups')
    plugins = acl_users.safi_users.plugins
    interface = plugins._getInterfaceFromName('IAuthenticationPlugin')
    if 'erp5_users' in list(plugins._getPlugins(interface)):
      plugins.deactivatePlugin( interface, 'erp5_users')
    interface = plugins._getInterfaceFromName('IUserEnumerationPlugin')
    if 'erp5_users' in list(plugins._getPlugins(interface)):
      plugins.deactivatePlugin( interface, 'erp5_users')

    # set properties to enable the login on Person and Organisation
    acl_users.safi_users.manage_changeProperties(portal_type_list=['Person',
                                                 'Organisation'],)
    acl_users.safi_groups.manage_changeProperties(portal_type_list=['Person', 
                                                 'Organisation'],)

  def checkRights(self, object_list, security_mapping, username):
    self.loginAsUser(username)
    user = getSecurityManager().getUser()
    if type(object_list) != type([]):
      object_list = [object_list,]
    for object in object_list:
      for permission, has in security_mapping.items():
        if user.has_permission(permission, object) and not has:
          self.fail('%s Permission should be Unauthorized on %s\n%s' % \
                                                ( permission,
                                                  object.getRelativeUrl(),
                                                  object.Base_viewSecurity()))
        if not(user.has_permission(permission, object)) and has:
          self.fail('%s Permission should be Authorized on %s\n%s' % \
                                                ( permission,
                                                  object.getRelativeUrl(),
                                                  object.Base_viewSecurity()))

  def checkTransition(self, object_list, possible_transition_list, 
                      not_possible_transition_list, username):
    
    if type(object_list) != type([]):
      object_list = [object_list,]
    for object in object_list:
      for transition in possible_transition_list:
        self.failUnlessUserCanPassWorkflowTransition(username, transition, 
                                                     object)
      for transition in not_possible_transition_list:
        self.failIfUserCanPassWorkflowTransition(username, transition, object)
