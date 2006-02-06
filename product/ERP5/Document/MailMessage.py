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

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

from Products.CMFMailIn.MailMessage import MailMessage as CMFMailInMessage
from Products.ERP5Type import Permissions, PropertySheet, Constraint, Interface
from Products.ERP5Type.XMLObject import XMLObject
from Products.CMFCore.WorkflowCore import WorkflowMethod

from Products.ERP5.Document.Event import Event
import smtplib

from zLOG import LOG

class MailMessage(XMLObject, Event, CMFMailInMessage):
    """
      MailMessage subclasses Event objects to implement Email Events.
    """

    meta_type = 'ERP5 Mail Message'
    portal_type = 'Mail Message'
    add_permission = Permissions.AddPortalContent
    isPortalContent = 1
    isRADContent = 1

    # Declarative security
    security = ClassSecurityInfo()
    security.declareObjectProtected(Permissions.AccessContentsInformation)

    # Declarative properties
    property_sheets = ( PropertySheet.Base
                      , PropertySheet.XMLObject
                      , PropertySheet.DublinCore
                      , PropertySheet.Task
                      , PropertySheet.Arrow
                      , PropertySheet.MailMessage
                      )

    def __init__(self, *args, **kw):
      attachments = kw.get('attachments', {})
      if kw.has_key('attachments'):
        del kw['attachments']
      XMLObject.__init__(self, *args, **kw)
      self.attachments = attachments

    def _edit(self, *args, **kw):
      LOG('MailMessage._edit', 0, str(kw))
      attachments = kw.get('attachments', {})
      if kw.has_key('attachments'):
        del kw['attachments']
      XMLObject._edit(self, *args, **kw)
      self.attachments = attachments

    def send(self, from_url=None, to_url=None, msg=None, subject=None):
      """
      Sends a reply to this mail message.
      """
      # We assume by default that we are replying to the sender
      if from_url == None:
        from_url = self.getUrlString()
      if to_url == None:
        to_url = self.getSender()
      if msg is not None and subject is not None:
        header = "From: %s\n" % from_url
        header += "To: %s\n\n" % to_url
        header += "Subject: %s\n" % subject
        header += "\n"
        msg = header + msg
        self.MailHost.send( msg )

    def getReplyBody(self):
      """
      This is used in order to respond to a mail,
      this put a '> ' before each line of the body
      """
      reply_body = ''
      if type(self.body) is type('a'):
        reply_body = '> ' + self.body.replace('\n','\n> ')
      return reply_body

    def getReplySubject(self):
      """
      This is used in order to respond to a mail,
      this put a 'Re: ' before the orignal subject
      """
      reply_subject = self.getTitle()
      if reply_subject.find('Re: ')!=0:
        reply_subject = 'Re: ' + reply_subject
      return reply_subject
  
