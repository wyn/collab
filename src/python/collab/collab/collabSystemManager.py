# Copyright (c) Simon Parry.
# See LICENSE for details.

import xmlrpclib as rpc

from twisted.python import log
from twisted.words.protocols.jabber import jid
from wokkel import disco, pubsub
from wokkel.iwokkel import IDisco
from zope.interface import implements

import collab
from collab import xmppMenuSystem as xmenu, xmppCommandSystem as xcmd, wizards


class CollabSystemManager(pubsub.PubSubClient):
    """
    This handler allows a system admin to configure a collab ecosystem
    can create other collabNodes or register/unregister machines to the system
    """
    implements(IDisco)

    def __init__(self, jid, name=None):
        self.jid = jid
        self.name = name or 'Collab System Manager'

        self.menu = xmenu.XmppMenuSystem(
            entity=self.jid,
            nodeIdentifier='collabManager',
            name=self.name
            )

        self.commandHandler = xcmd.PassThroughHandler()
        self.discoClient = disco.DiscoClientProtocol()
        self.xmlrpc = rpc.Server(collab.XMLRPC_URL)
                
    def setHandlerParent(self, parent):
        super(CollabSystemManager, self).setHandlerParent(parent)
        self.discoClient.setHandlerParent(parent)
        
    def connectionMade(self):
        # make into ad-hod command handler
        self.xmlstream.addObserver(collab.COMMAND_SET, self.handleRequest)
        
        getPSNodes = wizards.getPSNodes(self.discoClient, self.jid)
        getAdmins = wizards.getAllUsers(self.discoClient, jid.JID(collab.COLLAB_HOST), self.jid)
        getHosts = wizards.getHosts(self.xmlrpc)
        getPublishers = wizards.getPublishers
        getComponents = wizards.getComponents
        # communications sub menus - want client to be connected so doing this here
        h = wizards.makeSubSystemCommands(
            self.menu, self.jid, self.commandHandler, 'Communication Channels', 'comms_channels',
            dict({
            'Add': wizards.AddCommsWizardFactory(self.jid, self, getAdmins, getPublishers, getComponents),
            'Delete': wizards.DeleteCommsWizardFactory(self.jid, self, getPSNodes),
            'Configure channel': wizards.ConfigureCommsWizardFactory(self.jid, self, getPSNodes, getAdmins, getPublishers),
            }))
        # machines sub menus
        h = wizards.makeSubSystemCommands(
            self.menu, self.jid, h, 'Calculation Nodes', 'calcs_nodes',
            dict({
            'Add': wizards.AddMachineWizardFactory(self.jid, getHosts, self.xmlrpc),
            'Remove': wizards.RemoveMachineWizardFactory(self.jid, getHosts, self.xmlrpc),
            }))
        # collab nodes sub menus
        h = wizards.makeSubSystemCommands(
            self.menu, self.jid, h, 'Collab Nodes', 'collabs_nodes',
            dict({
            'Add': wizards.AddCollabWizardFactory(self.jid, getHosts, getComponents),
            }))
        
    def getDiscoInfo(self, requestor, target, nodeIdentifier=''):
        """
        Get identity and features from this entity, node.

        @param requestor: The entity the request originated from.
        @type requestor: L{jid.JID}
        @param target: The target entity to which the request is made.
        @type target: L{jid.JID}
        @param nodeIdentifier: The optional identifier of the node at this
                               entity to retrieve the identify and features of.
                               The default is C{''}, meaning the root node.
        @type nodeIdentifier: C{unicode}
        """
        if target != self.jid:
            log.msg('Bad JID %s' % target)            
            return
        
        if not nodeIdentifier:
            # root node
            info, _, _ = self.menu[self.menu.top]
            return info
        else:
            try:
                info, _, _ = self.menu[nodeIdentifier]
            except KeyError as e:
                log.msg(e)
            else:
                return info

        return

    
    def getDiscoItems(self, requestor, target, nodeIdentifier=''):
        """
        Get contained items for this entity, node.

        @param requestor: The entity the request originated from.
        @type requestor: L{jid.JID}
        @param target: The target entity to which the request is made.
        @type target: L{jid.JID}
        @param nodeIdentifier: The optional identifier of the node at this
                               entity to retrieve the identify and features of.
                               The default is C{''}, meaning the root node.
        @type nodeIdentifier: C{unicode}
        """
        if target != self.jid:
            log.msg('Bad JID %s' % target)
            return []

        if not nodeIdentifier:
            # root node
            return self.menu.getChildItems(self.menu.top)
        else:
            try:
                return self.menu.getChildItems(nodeIdentifier)
            except KeyError as e:
                log.msg(e)

        return []


    def handleRequest(self, iq):
        d = self.commandHandler.process_iq(iq)
        d.addCallback(self.xmlstream.send)
        return d
