##############################################################################
#
# Copyright (c) 2002-2010 Nexedi SA and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.
#
##############################################################################

from AccessControl import ClassSecurityInfo
from Products.ERP5Type import Permissions, PropertySheet
from Products.ERP5Type.XMLObject import XMLObject

class WebServiceConnector(XMLObject):
  # CMF Type Definition
  meta_type = 'ERP5 Web Service Connector'
  portal_type = 'Web Service Connector'

  # Declarative security
  security = ClassSecurityInfo()
  security.declareObjectProtected(Permissions.AccessContentsInformation)

  # Default Properties
  property_sheets = ( PropertySheet.Base
                      , PropertySheet.XMLObject
                      , PropertySheet.CategoryCore
                      , PropertySheet.DublinCore
                      , PropertySheet.SimpleItem
                      , PropertySheet.Login
                      , PropertySheet.Url
                      , PropertySheet.WebServiceConnector
                      )

  security.declarePublic('reset')
  def reset(self):
    """ Reset volatile variable
    """
    if getattr(self, '_v_conn', None) is not None:
      delattr(self, '_v_conn')

  security.declarePublic('getConnection')
  def getConnection(self):
    """ Return a connection to a web service
    """
    if getattr(self, '_v_conn', None) is None:
      self._v_conn = self.portal_web_services.connect(
          url = self.getUrlString(),
          user_name = self.getUserId(),
          password = self.getPassword(),
          transport = self.getTransport(),
      )
    return self._v_conn
