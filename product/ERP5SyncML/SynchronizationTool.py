## Copyright (c) 2002 Nexedi SARL and Contributors. All Rights Reserved.
#          Sebastien Robin <seb@nexedi.com>
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

"""\
ERP portal_synchronizations tool.
"""

from OFS.SimpleItem import SimpleItem
from OFS.Folder import Folder
from Products.CMFCore.utils import UniqueObject
from Globals import InitializeClass, DTMLFile, PersistentMapping, Persistent
from AccessControl import ClassSecurityInfo, getSecurityManager
from Products.CMFCore import CMFCorePermissions
from Products.ERP5SyncML import _dtmldir
from Publication import Publication,Subscriber
from Subscription import Subscription,Signature
from xml.dom.ext.reader.Sax2 import FromXmlStream, FromXml
from XMLSyncUtils import *
from Products.ERP5Type import Permissions
from PublicationSynchronization import PublicationSynchronization
from SubscriptionSynchronization import SubscriptionSynchronization
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import noSecurityManager
from AccessControl.User import UnrestrictedUser
from Acquisition import aq_base
import urllib
import urllib2
import socket
import os
import string
import commands
import random
from zLOG import *


from Conduit.ERP5Conduit import ERP5Conduit

class SynchronizationError( Exception ):
  pass

class SynchronizationTool( UniqueObject, SimpleItem,
                           SubscriptionSynchronization, PublicationSynchronization ):
  """
    This tool implements the synchronization algorithm
  """


  id       = 'portal_synchronizations'
  meta_type    = 'ERP5 Synchronizations'

  security = ClassSecurityInfo()

  #
  #  Default values.
  #
  list_publications = PersistentMapping()
  list_subscriptions = PersistentMapping()

  # Do we want to use emails ?
  #email = None
  email = 1
  same_export = 1

  def __init__( self ):
    self.list_publications = PersistentMapping()
    self.list_subscriptions = PersistentMapping()

  #
  #  ZMI methods
  #
  manage_options = ( ( { 'label'   : 'Overview'
             , 'action'   : 'manage_overview'
             }
            , { 'label'   : 'Publications'
             , 'action'   : 'managePublications'
             }
            , { 'label'   : 'Subscriptions'
             , 'action'   : 'manageSubscriptions'
             }
            , { 'label'   : 'Conflicts'
             , 'action'   : 'manageConflicts'
             }
            )
           + SimpleItem.manage_options
           )

  security.declareProtected( CMFCorePermissions.ManagePortal
               , 'manage_overview' )
  manage_overview = DTMLFile( 'dtml/explainSynchronizationTool', globals() )

  security.declareProtected( CMFCorePermissions.ManagePortal
               , 'managePublications' )
  managePublications = DTMLFile( 'dtml/managePublications', globals() )

  security.declareProtected( CMFCorePermissions.ManagePortal
               , 'manage_addPublicationForm' )
  manage_addPublicationForm = DTMLFile( 'dtml/manage_addPublication', globals() )

  security.declareProtected( CMFCorePermissions.ManagePortal
               , 'manageSubsciptions' )
  manageSubscriptions = DTMLFile( 'dtml/manageSubscriptions', globals() )

  security.declareProtected( CMFCorePermissions.ManagePortal
               , 'manageConflicts' )
  manageConflicts = DTMLFile( 'dtml/manageConflicts', globals() )

  security.declareProtected( CMFCorePermissions.ManagePortal
               , 'manage_addSubscriptionForm' )
  manage_addSubscriptionForm = DTMLFile( 'dtml/manage_addSubscription', globals() )

  security.declareProtected( CMFCorePermissions.ManagePortal
               , 'editProperties' )
  def editProperties( self
           , publisher=None
           , REQUEST=None
           ):
    """
      Form handler for "tool-wide" properties (including list of
      metadata elements).
    """
    if publisher is not None:
      self.publisher = publisher

    if REQUEST is not None:
      REQUEST[ 'RESPONSE' ].redirect( self.absolute_url()
                    + '/propertiesForm'
                    + '?manage_tabs_message=Tool+updated.'
                    )

  security.declareProtected(Permissions.ModifyPortalContent, 'manage_addPublication')
  def manage_addPublication(self, id, publication_url, destination_path,
            query, xml_mapping, gpg_key, RESPONSE=None):
    """
      create a new publication
    """
    pub = Publication(id, publication_url, destination_path,
                      query, xml_mapping, gpg_key)
    if len(self.list_publications) == 0:
      self.list_publications = PersistentMapping()
    self.list_publications[id] = pub
    if RESPONSE is not None:
      RESPONSE.redirect('managePublications')

  security.declareProtected(Permissions.ModifyPortalContent, 'manage_addSubscription')
  def manage_addSubscription(self, id, publication_url, subscription_url,
                       destination_path, query, xml_mapping, gpg_key, RESPONSE=None):
    """
      XXX should be renamed as addSubscription
      create a new subscription
    """
    sub = Subscription(id, publication_url, subscription_url,
                       destination_path, query, xml_mapping, gpg_key)
    if len(self.list_subscriptions) == 0:
      self.list_subscriptions = PersistentMapping()
    self.list_subscriptions[id] = sub
    if RESPONSE is not None:
      RESPONSE.redirect('manageSubscriptions')

  security.declareProtected(Permissions.ModifyPortalContent, 'manage_editPublication')
  def manage_editPublication(self, id, publication_url, destination_path,
                       query, xml_mapping, gpg_key, RESPONSE=None):
    """
      modify a publication
    """
    pub = Publication(id, publication_url, destination_path,
                      query, xml_mapping, gpg_key)
    self.list_publications[id] = pub
    if RESPONSE is not None:
      RESPONSE.redirect('managePublications')

  security.declareProtected(Permissions.ModifyPortalContent, 'manage_editSubscription')
  def manage_editSubscription(self, id, publication_url, subscription_url,
             destination_path, query, xml_mapping, gpg_key, RESPONSE=None):
    """
      modify a subscription
    """
    sub = Subscription(id, publication_url, subscription_url,
                       destination_path, query, xml_mapping, gpg_key)
    self.list_subscriptions[id] = sub
    if RESPONSE is not None:
      RESPONSE.redirect('manageSubscriptions')

  security.declareProtected(Permissions.ModifyPortalContent, 'manage_deletePublication')
  def manage_deletePublication(self, id, RESPONSE=None):
    """
      delete a publication
    """
    del self.list_publications[id]
    if RESPONSE is not None:
      RESPONSE.redirect('managePublications')

  security.declareProtected(Permissions.ModifyPortalContent, 'manage_deleteSubscription')
  def manage_deleteSubscription(self, id, RESPONSE=None):
    """
      delete a subscription
    """
    del self.list_subscriptions[id]
    if RESPONSE is not None:
      RESPONSE.redirect('manageSubscriptions')

  security.declareProtected(Permissions.ModifyPortalContent, 'manage_resetPublication')
  def manage_resetPublication(self, id, RESPONSE=None):
    """
      reset a publication
    """
    self.list_publications[id].resetAllSubscribers()
    if RESPONSE is not None:
      RESPONSE.redirect('managePublications')

  security.declareProtected(Permissions.ModifyPortalContent, 'manage_resetSubscription')
  def manage_resetSubscription(self, id, RESPONSE=None):
    """
      reset a subscription
    """
    self.list_subscriptions[id].resetAllSignatures()
    self.list_subscriptions[id].resetAnchors()
    if RESPONSE is not None:
      RESPONSE.redirect('manageSubscriptions')

  security.declareProtected(Permissions.AccessContentsInformation,'getPublicationList')
  def getPublicationList(self):
    """
      Return a list of publications
    """
    return_list = []
    if type(self.list_publications) is type([]): # For compatibility with old
                                                 # SynchronizationTool, XXX To be removed
      self.list_publications = PersistentMapping()
    for key in self.list_publications.keys():
      LOG('getPublicationList',0,'key: %s, pub:%s' % (key,repr(self.list_publications[key])))
      return_list += [self.list_publications[key].__of__(self)]
    return return_list

  security.declareProtected(Permissions.AccessContentsInformation,'getPublication')
  def getPublication(self, id):
    """
      Return the  publications with this id
    """
    #self.list_publications=PersistentMapping()
    if self.list_publications.has_key(id):
      return self.list_publications[id].__of__(self)
    return None

  security.declareProtected(Permissions.AccessContentsInformation,'getSubscriptionList')
  def getSubscriptionList(self):
    """
      Return a list of publications
    """
    return_list = []
    if type(self.list_subscriptions) is type([]): # For compatibility with old
                                                 # SynchronizationTool, XXX To be removed
      self.list_subscriptions = PersistentMapping()
    for key in self.list_subscriptions.keys():
      return_list += [self.list_subscriptions[key].__of__(self)]
    return return_list

  def getSubscription(self, id):
    """
      Returns the subscription with this id
    """
    for subscription in self.getSubscriptionList():
      if subscription.getId()==id:
        return subscription
    return None


  security.declareProtected(Permissions.AccessContentsInformation,'getSynchronizationList')
  def getSynchronizationList(self):
    """
      Returns the list of subscriptions and publications

    """
    return self.getSubscriptionList() + self.getPublicationList()

  security.declareProtected(Permissions.AccessContentsInformation,'getSubscriberList')
  def getSubscriberList(self):
    """
      Returns the list of subscribers and subscriptions
    """
    s_list = []
    s_list += self.getSubscriptionList()
    for publication in self.getPublicationList():
      s_list += publication.getSubscriberList()
    return s_list

  security.declareProtected(Permissions.AccessContentsInformation,'getConflictList')
  def getConflictList(self, context=None):
    """
    Retrieve the list of all conflicts
    Here the list is as follow :
    [conflict_1,conflict2,...] where conflict_1 is like:
    ['publication',publication_id,object.getPath(),property_id,publisher_value,subscriber_value]
    """
    path = self.resolveContext(context)
    conflict_list = []
    for publication in self.getPublicationList():
      for subscriber in publication.getSubscriberList():
        sub_conflict_list = subscriber.getConflictList()
        for conflict in sub_conflict_list:
          #conflict.setDomain('Publication')
          conflict.setSubscriber(subscriber)
          #conflict.setDomainId(subscriber.getId())
          conflict_list += [conflict.__of__(self)]
    for subscription in self.getSubscriptionList():
      sub_conflict_list = subscription.getConflictList()
      for conflict in sub_conflict_list:
        #conflict.setDomain('Subscription')
        conflict.setSubscriber(subscription)
        #conflict.setDomainId(subscription.getId())
        conflict_list += [conflict.__of__(self)]
    if path is not None: # Retrieve only conflicts for a given path
      new_list = []
      for conflict in conflict_list:
        if conflict.getObjectPath() == path:
          new_list += [conflict.__of__(self)]
      return new_list
    return conflict_list

  security.declareProtected(Permissions.AccessContentsInformation,'getDocumentConflictList')
  def getDocumentConflictList(self, context=None):
    """
    Retrieve the list of all conflicts for a given document
    Well, this is the same thing as getConflictList with a path
    """
    return self.getConflictList(context)


  security.declareProtected(Permissions.AccessContentsInformation,'getSynchronizationState')
  def getSynchronizationState(self, context):
    """
    context : the context on which we are looking for state

    This functions have to retrieve the synchronization state,
    it will first look in the conflict list, if nothing is found,
    then we have to check on a publication/subscription.

    This method returns a mapping between subscription and states

    JPS suggestion:
      path -> object, document, context, etc.
      type -> '/titi/toto' or ('','titi', 'toto') or <Base instance 1562567>
      object = self.resolveContext(context) (method to add)
    """
    path = self.resolveContext(context)
    conflict_list = self.getConflictList()
    state_list= []
    LOG('getSynchronizationState',0,'path: %s' % str(path))
    for conflict in conflict_list:
      if conflict.getObjectPath() == path:
        LOG('getSynchronizationState',0,'found a conflict: %s' % str(conflict))
        state_list += [[conflict.getSubscriber(),self.CONFLICT]]
    for domain in self.getSynchronizationList():
      destination = domain.getDestinationPath()
      LOG('getSynchronizationState',0,'destination: %s' % str(destination))
      j_path = '/'.join(path)
      LOG('getSynchronizationState',0,'j_path: %s' % str(j_path))
      if j_path.find(destination)==0:
        o_id = j_path[len(destination)+1:].split('/')[0]
        LOG('getSynchronizationState',0,'o_id: %s' % o_id)
        subscriber_list = []
        if domain.domain_type==self.PUB:
          subscriber_list = domain.getSubscriberList()
        else:
          subscriber_list = [domain]
        LOG('getSynchronizationState, subscriber_list:',0,subscriber_list)
        for subscriber in subscriber_list:
          signature = subscriber.getSignature(o_id)
          if signature is not None:
            state = signature.getStatus()
            LOG('getSynchronizationState:',0,'sub.dest :%s, state: %s' % \
                                   (subscriber.getSubscriptionUrl(),str(state)))
            found = None
            # Make sure there is not already a conflict giving the state
            for state_item in state_list:
              if state_item[0]==subscriber:
                found = 1
            if found is None:
              state_list += [[subscriber,state]]
    return state_list

  security.declareProtected(Permissions.ModifyPortalContent, 'applyPublisherValue')
  def applyPublisherValue(self, conflict):
    """
      after a conflict resolution, we have decided
      to keep the local version of an object
    """
    object = self.unrestrictedTraverse(conflict.getObjectPath())
    subscriber = conflict.getSubscriber()
    # get the signature:
    LOG('p_sync.applyPublisherValue, subscriber: ',0,subscriber)
    signature = subscriber.getSignature(object.getId()) # XXX may be change for rid
    signature.delConflict(conflict)
    if signature.getConflictList() == []:
      LOG('p_sync.applyPublisherValue, conflict_list empty on : ',0,signature)
      signature.setStatus(self.PUB_CONFLICT_MERGE)

  security.declareProtected(Permissions.ModifyPortalContent, 'applyPublisherDocument')
  def applyPublisherDocument(self, conflict):
    """
    apply the publisher value for all conflict of the given document
    """
    subscriber = conflict.getSubscriber()
    LOG('applyPublisherDocument, subscriber: ',0,subscriber)
    for c in self.getConflictList(conflict.getObjectPath()):
      if c.getSubscriber() == subscriber:
        LOG('applyPublisherDocument, applying on conflict: ',0,conflict)
        c.applyPublisherValue()

  security.declareProtected(Permissions.ModifyPortalContent, 'applySubscriberDocument')
  def applySubscriberDocument(self, conflict):
    """
    apply the subscriber value for all conflict of the given document
    """
    subscriber = conflict.getSubscriber()
    for c in self.getConflictList(conflict.getObjectPath()):
      if c.getSubscriber() == subscriber:
        c.applySubscriberValue()

  security.declareProtected(Permissions.ModifyPortalContent, 'applySubscriberValue')
  def applySubscriberValue(self, conflict):
    """
      after a conflict resolution, we have decided
      to keep the local version of an object
    """
    object = self.unrestrictedTraverse(conflict.getObjectPath())
    subscriber = conflict.getSubscriber()
    # get the signature:
    LOG('p_sync.setRemoteObject, subscriber: ',0,subscriber)
    signature = subscriber.getSignature(object.getId()) # XXX may be change for rid
    conduit = ERP5Conduit()
    for xupdate in conflict.getXupdateList():
      conduit.updateNode(xml=xupdate,object=object,force=1)
    signature.delConflict(conflict)
    if signature.getConflictList() == []:
      signature.setStatus(self.PUB_CONFLICT_MERGE)


  security.declareProtected(Permissions.ModifyPortalContent, 'manageLocalValue')
  def managePublisherValue(self, subscription_url, property_id, object_path, RESPONSE=None):
    """
    Do whatever needed in order to store the local value on
    the remote server

    Suggestion (API)
      add method to view document with applied xupdate
      of a given subscriber XX (ex. viewSubscriberDocument?path=ddd&subscriber_id=dddd)
      Version=Version CPS
    """
    # Retrieve the conflict object
    LOG('manageLocalValue',0,'%s %s %s' % (str(subscription_url),
                                           str(property_id),
                                           str(object_path)))
    for conflict in self.getConflictList():
      LOG('manageLocalValue, conflict:',0,conflict)
      if conflict.getPropertyId() == property_id:
        LOG('manageLocalValue',0,'found the property_id')
        if '/'.join(conflict.getObjectPath())==object_path:
          if conflict.getSubscriber().getSubscriptionUrl()==subscription_url:
            conflict.applyPublisherValue()
    if RESPONSE is not None:
      RESPONSE.redirect('manageConflicts')

  security.declareProtected(Permissions.ModifyPortalContent, 'manageRemoteValue')
  def manageSubscriberValue(self, subscription_url, property_id, object_path, RESPONSE=None):
    """
    Do whatever needed in order to store the remote value locally
    and confirmed that the remote box should keep it's value
    """
    LOG('manageLocalValue',0,'%s %s %s' % (str(subscription_url),
                                           str(property_id),
                                           str(object_path)))
    for conflict in self.getConflictList():
      LOG('manageLocalValue, conflict:',0,conflict)
      if conflict.getPropertyId() == property_id:
        LOG('manageLocalValue',0,'found the property_id')
        if '/'.join(conflict.getObjectPath())==object_path:
          if conflict.getSubscriber().getSubscriptionUrl()==subscription_url:
            conflict.applySubscriberValue()
    if RESPONSE is not None:
      RESPONSE.redirect('manageConflicts')

  def resolveContext(self, context):
    """
    We try to return a path (like ('','erp5','foo') from the context.
    Context can be :
      - a path
      - an object
      - a string representing a path
    """
    if context is None:
      return context
    elif type(context) is type(()):
      return context
    elif type(context) is type('a'):
      return tuple(context.split('/'))
    else:
      return context.getPhysicalPath()

  security.declarePublic('sendResponse')
  def sendResponse(self, to_url=None, from_url=None, sync_id=None,xml=None, domain=None, send=1):
    """
    We will look at the url and we will see if we need to send mail, http
    response, or just copy to a file.
    """
    LOG('sendResponse, self.getPhysicalPath: ',0,self.getPhysicalPath())
    LOG('sendResponse, to_url: ',0,to_url)
    LOG('sendResponse, from_url: ',0,from_url)
    LOG('sendResponse, sync_id: ',0,sync_id)
    LOG('sendResponse, xml: ',0,xml)
    if domain is not None:
      gpg_key = domain.getGPGKey()
      if gpg_key not in ('',None):
        filename = str(random.randrange(1,2147483600)) + '.txt'
        decrypted = file('/tmp/%s' % filename,'w')
        decrypted.write(xml)
        decrypted.close()
        (status,output)=commands.getstatusoutput('gzip /tmp/%s' % filename)
        (status,output)=commands.getstatusoutput('gpg --yes --homedir /var/lib/zope/Products/ERP5SyncML/gnupg_keys -r "%s" -se /tmp/%s.gz' % (gpg_key,filename))
        LOG('readResponse, gpg output:',0,output)
        encrypted = file('/tmp/%s.gz.gpg' % filename,'r')
        xml = encrypted.read()
        encrypted.close()
        commands.getstatusoutput('rm -f /tmp/%s.gz' % filename)
        commands.getstatusoutput('rm -f /tmp/%s.gz.gpg' % filename)
    if send:
      if type(to_url) is type('a'):
        if to_url.find('http://')==0:
          # XXX Make sure this is not a problem
          if domain.domain_type == self.PUB:
            return None
          # we will send an http response
          domain = aq_base(domain)
          self.activate(activity='RAMQueue').sendHttpResponse(sync_id=sync_id,
                                           to_url=to_url,
                                           xml=xml, domain=domain)
          return None
        elif to_url.find('file://')==0:
          filename = to_url[len('file:/'):]
          stream = file(filename,'w')
          LOG('sendResponse, filename: ',0,filename)
          stream.write(xml)
          stream.close()
          # we have to use local files (unit testing for example
        elif to_url.find('mailto:')==0:
          # we will send an email
          to_address = to_url[len('mailto:'):]
          from_address = from_url[len('mailto:'):]
          self.sendMail(from_address,to_address,sync_id,xml)
    return xml

  security.declarePrivate('sendHttpResponse')
  def sendHttpResponse(self, to_url=None, sync_id=None, xml=None, domain=None ):
    LOG('sendHttpResponse, self.getPhysicalPath: ',0,self.getPhysicalPath())
    LOG('sendHttpResponse, starting with domain:',0,domain)
    LOG('sendHttpResponse, xml:',0,xml)
    if domain is not None:
      if domain.domain_type == self.PUB:
        return xml
    # Retrieve the proxy from os variables
    proxy_url = ''
    if os.environ.has_key('http_proxy'):
      proxy_url = os.environ['http_proxy']
    LOG('sendHttpResponse, proxy_url:',0,proxy_url)
    if proxy_url !='':
      proxy_handler = urllib2.ProxyHandler({"http" :proxy_url})
    else:
      proxy_handler = urllib2.ProxyHandler({})
    pass_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
    auth_handler = urllib2.HTTPBasicAuthHandler(pass_mgr)
    proxy_auth_handler = urllib2.ProxyBasicAuthHandler(pass_mgr)
    opener = urllib2.build_opener(proxy_handler, proxy_auth_handler,auth_handler,urllib2.HTTPHandler)
    urllib2.install_opener(opener)
    to_encode = {'text':xml,'sync_id':sync_id}
    encoded = urllib.urlencode(to_encode)
    to_url = to_url + '/portal_synchronizations/readResponse'
    request = urllib2.Request(url=to_url,data=encoded)
    #result = urllib2.urlopen(request).read()
    try:
      result = urllib2.urlopen(request).read()
    except socket.error, msg:
      self.activate(activity='RAMQueue').sendHttpResponse(to_url=to_url,sync_id=sync_id,xml=xml,domain=domain)
      LOG('sendHttpResponse, socket ERROR:',0,msg)
      return

    
    LOG('sendHttpResponse, before result, domain:',0,domain)
    LOG('sendHttpResponse, result:',0,result)
    if domain is not None:
      if domain.domain_type == self.SUB:
        gpg_key = domain.getGPGKey()
        if result not in (None,''):
          #if gpg_key not in ('',None):
          #  result = self.sendResponse(domain=domain,xml=result,send=0)
          uf = self.acl_users
          user = UnrestrictedUser('syncml','syncml',['Manager','Member'],'')
          newSecurityManager(None, user)
          self.activate(activity='RAMQueue').readResponse(sync_id=sync_id,text=result)

  security.declarePublic('sync')
  def sync(self):
    """
    This will try to synchronize every subscription
    """
    # Login as a manager to make sure we can create objects
    uf = self.acl_users
    user = UnrestrictedUser('syncml','syncml',['Manager','Member'],'')
    newSecurityManager(None, user)
    message_list = self.portal_activities.getMessageList()
    LOG('sync, message_list:',0,message_list)
    if len(message_list) == 0:
      for subscription in self.getSubscriptionList():
        LOG('sync, subcription:',0,subscription)
        self.activate(activity='RAMQueue').SubSync(subscription.getId())

  security.declarePublic('readResponse')
  def readResponse(self, text=None, sync_id=None, to_url=None, from_url=None):
    """
    We will look at the url and we will see if we need to send mail, http
    response, or just copy to a file.
    """
    LOG('readResponse, ',0,'starting')
    LOG('readResponse, self.getPhysicalPath: ',0,self.getPhysicalPath())
    LOG('readResponse, sync_id: ',0,sync_id)
    LOG('readResponse, text:',0,text)
    # Login as a manager to make sure we can create objects
    uf = self.acl_users
    user = UnrestrictedUser('syncml','syncml',['Manager','Member'],'')
    newSecurityManager(None, user)

    if text is not None:
      # XXX We will look everywhere for a publication/subsription with
      # the id sync_id, this is not so good, but there is no way yet
      # to know if we will call a publication or subscription XXX
      gpg_key = ''
      for publication in self.getPublicationList():
        if publication.getId()==sync_id:
          gpg_key = publication.getGPGKey()
      if gpg_key == '':
        for subscription in self.getSubscriptionList():
          if subscription.getId()==sync_id:
            gpg_key = subscription.getGPGKey()
      # decrypt the message if needed
      if gpg_key not in (None,''):
        filename = str(random.randrange(1,2147483600)) + '.txt'
        encrypted = file('/tmp/%s.gz.gpg' % filename,'w')
        encrypted.write(text)
        encrypted.close()
        (status,output)=commands.getstatusoutput('gpg --homedir /var/lib/zope/Products/ERP5SyncML/gnupg_keys -r "%s"  --decrypt /tmp/%s.gz.gpg > /tmp/%s.gz' % (gpg_key,filename,filename))
        LOG('readResponse, gpg output:',0,output)
        (status,output)=commands.getstatusoutput('gunzip /tmp/%s.gz' % filename)
        decrypted = file('/tmp/%s' % filename,'r')
        text = decrypted.read()
        LOG('readResponse, text:',0,text)
        decrypted.close()
        commands.getstatusoutput('rm -f /tmp/%s' % filename)
        commands.getstatusoutput('rm -f /tmp/%s.gz.gpg' % filename)
      # Get the target and then find the corresponding publication or
      # Subscription
      xml = FromXml(text)
      url = ''
      for subnode in self.getElementNodeList(xml):
        if subnode.nodeName == 'SyncML':
          for subnode1 in self.getElementNodeList(subnode):
            if subnode1.nodeName == 'SyncHdr':
              for subnode2 in self.getElementNodeList(subnode1):
                if subnode2.nodeName == 'Target':
                  url = subnode2.childNodes[0].data 
      for publication in self.getPublicationList():
        if publication.getPublicationUrl()==url and publication.getId()==sync_id:
          result = self.PubSync(sync_id,xml)
          # Then encrypt the message
          xml = result['xml']
          xml = self.sendResponse(xml=xml,domain=publication,send=0)
          return xml
      for subscription in self.getSubscriptionList() and subscription.getId()==sync_id:
        if subscription.getSubscriptionUrl()==url:
          result = self.activate(activity='RAMQueue').SubSync(sync_id,xml)
          #result = self.SubSync(sync_id,xml)

    # we use from only if we have a file 
    elif type(from_url) is type('a'):
      if from_url.find('file://')==0:
        try:
          filename = from_url[len('file:/'):]
          stream = file(filename,'r')
          xml = stream.read()
          #stream.seek(0)
          #LOG('readResponse',0,'Starting... msg: %s' % str(stream.read()))
        except IOError:
          LOG('readResponse, cannot read file: ',0,filename)
          xml = None
        if xml is not None and len(xml)==0:
          xml = None
        return xml

InitializeClass( SynchronizationTool )
