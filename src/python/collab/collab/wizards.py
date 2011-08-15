# Copyright (c) Simon Parry.
# See LICENSE for details.

from twisted.internet import defer, threads
from twisted.python import log
from twisted.words.protocols.jabber import jid
from wokkel import disco
from zope.interface import implements, Interface

import collab
from collab import xmppCommandSystem as xcmd, stateManager as sm, pageManager as pm, pages


def getHosts(rpc_server):

    def xmlrpcRequest():
        d_hosts = threads.deferToThread(rpc_server.host_list, {})
        # returns e.g. {'hosts': [{'host': 'localhost'}, {'host': 'master.local'}]}
        def makeHosts(hosts):
            hs = []
            try:
                hostnames = hosts['hosts']
            except KeyError:
                log.msg('Cannot find any host names in %s' % hosts)
                return hs

            for dic in hostnames:
                try:
                    hs.append(dic['host'])
                except KeyError:
                    log.msg('No host name found for %s' % dic)
                    pass

            return hs

        d_hosts.addCallback(makeHosts)
        return d_hosts
    
    return xmlrpcRequest

def getPublishers():
    def discoRequest():
        dsc = disco.DiscoItems()
        [dsc.append(disco.DiscoItem(jid.JID(j))) for j in ['%s.%s' % (nm, collab.COLLAB_HOST) for nm in collab.SERVICES.values()]]

        return defer.succeed(dsc)

    return discoRequest

def getAllUsers(discoClient, server, sender):

    def discoRequest():
        return discoClient.requestItems(entity=server, nodeIdentifier='all users', sender=sender)

    return discoRequest

def getComponents():
    """
    Friendly names for services
    """
    def discoRequest():
        return defer.succeed(collab.COLLAB_COMPONENTS)

    return discoRequest

def getPSNodes(discoClient, sender):

    def discoRequest():
        return discoClient.requestItems(entity=jid.JID(collab.PUBSUB_NODE), sender=sender)
    
    return discoRequest


class IWizard(Interface):
    def addCommand(sub_top, name, handler, menu):
        pass

class Wizard(object):
    implements(IWizard)

    def __init__(self, jid, stateManager, pageManager, withPrev=False):
        self.jid = jid
        self.stateManager = stateManager
        self.pageManager = pageManager
        self.withPrev = withPrev
        
    def addCommand(self, sub_top, name, handler, menu):
        node = self._addSubMenu(sub_top, name, menu)
        return self._addHandlers(node, handler)

    def _addSubMenu(self, sub_top, name, menu):
        node = '%s_%s' % (sub_top, name)
        menu.addSubMenu(
            entity=self.jid,
            nodeIdentifier=node,
            parentNodeIdentifier=sub_top,
            category='automation',
            idType='command-node',
            name=name
            )
        return node

    def _addHandlers(self, node, handler):
        n = xcmd.NodeHandler(node, self.stateManager, self.pageManager)
        cancel = xcmd.CancelHandler(node, self.stateManager, self.pageManager)
        start = xcmd.StartHandler(node, self.stateManager, self.pageManager)

        if self.withPrev:
            prev = xcmd.PrevHandler(node, self.stateManager, self.pageManager)
            prev.set_successor(n)
            cancel.set_successor(prev)
        else:
            cancel.set_successor(n)

        start.set_successor(cancel)
        handler.set_successor(start)

        return n

    
class IWizardFactory(Interface):
    def build():
        pass

    
class AddMachineWizardFactory(object):
    implements(IWizardFactory)
    
    def __init__(self, jid, getRegistered, xmlrpc):
        self.jid = jid
        self.getRegistered = getRegistered
        self.xmlrpc = xmlrpc
        
    def build(self):
        changer = sm.RegisterMachineStateChanger(self.xmlrpc)
        stateManager = sm.StateManager(changer)

        pageManager = pm.PageManager()
        pageManager.add_page(pages.RegisterMachinePage(self.getRegistered))
        pageManager.add_page(pages.EndPage('Registered a machine with the Collab system'))

        return Wizard(self.jid, stateManager, pageManager)

    
class RemoveMachineWizardFactory(object):
    implements(IWizardFactory)
    
    def __init__(self, jid, getRegistered, xmlrpc):
        self.jid = jid
        self.getRegistered = getRegistered
        self.xmlrpc = xmlrpc

    def build(self):
        changer = sm.UnregisterMachineStateChanger(self.xmlrpc)
        stateManager = sm.StateManager(changer)

        pageManager = pm.PageManager()
        pageManager.add_page(pages.UnregisterMachinePage(self.getRegistered))
        pageManager.add_page(pages.EndPage('Unregistered the machine from the Collab system'))

        return Wizard(self.jid, stateManager, pageManager)

    
class AddCollabWizardFactory(object):
    implements(IWizardFactory)
    
    def __init__(self, jid, getRegistered, getComponents):
        self.jid = jid
        self.getRegistered = getRegistered
        self.getComponents = getComponents

    def build(self):
        changer = sm.CreateCollabNodeStateChanger()
        stateManager = sm.StateManager(changer)

        pageManager = pm.PageManager()
        pageManager.add_page(pages.CreateCollabNodePage(self.getRegistered, self.getComponents))
        pageManager.add_page(pages.EndPage('Created a new Collab node'))

        return Wizard(self.jid, stateManager, pageManager)


class AddCommsWizardFactory(object):
    implements(IWizardFactory)
    
    def __init__(self, jid, psclient, getAdmins, getPublishers, getComponents):
        self.jid = jid
        self.psclient = psclient
        self.getAdmins = getAdmins
        self.getPublishers = getPublishers
        self.getComponents = getComponents
        
    def build(self):
        changer = sm.CreatePubsubNodeStateChanger(self.psclient, self.jid)
        stateManager = sm.StateManager(changer)

        pageManager = pm.PageManager()
        pageManager.add_page(pages.CreatePubsubNodePage(self.getComponents))
        pageManager.add_page(pages.ConfigurePubsubNodeOwnersPage(self.getAdmins))
        pageManager.add_page(pages.ConfigurePubsubNodePublishersPage(self.getPublishers))
        pageManager.add_page(pages.ConfigurePubsubNodeSubscribersPage(self.getPublishers))
        pageManager.add_page(pages.EndPage('Created a new communications channel'))

        return Wizard(self.jid, stateManager, pageManager, True)

class ConfigureCommsWizardFactory(object):
    implements(IWizardFactory)
    
    def __init__(self, jid, psclient, getPSNodes, getAdmins, getPublishers):
        self.jid = jid
        self.psclient = psclient
        self.getPSNodes = getPSNodes
        self.getAdmins = getAdmins
        self.getPublishers = getPublishers

    def build(self):
        changer = sm.ConfigPubsubNodeStateChanger(self.psclient, self.jid)
        stateManager = sm.StateManager(changer)

        pageManager = pm.PageManager()
        pageManager.add_page(pages.InplaceConfigurePubsubNodePage(self.getPSNodes))
        pageManager.add_page(pages.ConfigurePubsubNodeOwnersPage(self.getAdmins))
        pageManager.add_page(pages.ConfigurePubsubNodePublishersPage(self.getPublishers))
        pageManager.add_page(pages.ConfigurePubsubNodeSubscribersPage(self.getPublishers))
        pageManager.add_page(pages.EndPage('Configured the communications channel'))

        return Wizard(self.jid, stateManager, pageManager, True)

    
class DeleteCommsWizardFactory(object):
    implements(IWizardFactory)
    
    def __init__(self, jid, psclient, getPSNodes):
        self.jid = jid
        self.psclient = psclient
        self.getPSNodes = getPSNodes

    def build(self):
        changer = sm.DeletePubsubNodeStateChanger(self.psclient, self.jid)
        stateManager = sm.StateManager(changer)

        pageManager = pm.PageManager()
        pageManager.add_page(pages.DeletePubsubNodePage(self.getPSNodes))
        pageManager.add_page(pages.EndPage('Deleted communications channel'))

        return Wizard(self.jid, stateManager, pageManager, False)

class ViewCollabNodeWizardFactory(object):
    """
    ViewCollabNodeWizardFactory: Factory that builds the wizard for viewing the setup of a Collab node
    
    @ivar jid: The sender
    @type jid: L{jid.JID}
    
    """
    implements(IWizardFactory)
    
    def __init__(self, jid, inputNode, outputNode, errorNode):
        self.jid = jid
        self.inputNode = inputNode
        self.outputNode = outputNode
        self.errorNode = errorNode
        
    def build(self):
        changer = sm.NullStateChanger()
        stateManager = sm.StateManager(changer)

        pageManager = pm.PageManager()
        pageManager.add_page(pages.ViewCollabChannelsPage(self.jid, self.inputNode, self.outputNode, self.errorNode))
        pageManager.add_page(pages.EndPage('Done'))

        return Wizard(self.jid, stateManager, pageManager)

    
class ConfigureCollabLoadBalancingWizardFactory(object):
    implements(IWizardFactory)
    
    def __init__(self, jid, loadBalancer):
        self.jid = jid
        self.loadBalancer = loadBalancer

    def build(self):
        changer = sm.ConfigureLoadBalancerStateChanger(self.loadBalancer)
        stateManager = sm.StateManager(changer)

        pageManager = pm.PageManager()
        pageManager.add_page(pages.ConfigureCollabNodeLoadBalancerPage())
        pageManager.add_page(pages.EndPage('Configured the load balancer'))

        return Wizard(self.jid, stateManager, pageManager)

    
class LargeHomogeneousPortfolioWizardFactory(object):
    """
    LargeHomogeneousPortfolioWizardFactory: Factory class for building a wizard for running the LHP simulation
    
    @ivar jid: The JID of the sender
    @type jid: L{jid.JID}
    
    """
    def __init__(self, jid, broadcaster):
        self.jid = jid
        self.broadcaster = broadcaster
        
    def build(self):
        changer = sm.LHPPortfolioStateChanger(self.broadcaster)
        stateManager = sm.StateManager(changer)

        pageManager = pm.PageManager()
        pageManager.add_page(pages.LHPPortfolioPage())
        pageManager.add_page(pages.EndPage('Running Large Homogeneous Portfolio simulation'))

        return Wizard(self.jid, stateManager, pageManager)


class ClientRegisterWizardFactory(object):
    """
    ClientRegisterWizardFactory: Factory class for building a wizard for registering a client
    with a specific sub system.
    
    @ivar jid: The JID of the sender
    @type jid: L{jid.JID}
    
    """
    def __init__(self, jid, registration):
        self.jid = jid
        self.registration = registration
        
    def build(self):
        changer = sm.ClientRegisterStateChanger(self.registration)
        stateManager = sm.StateManager(changer)

        pageManager = pm.PageManager()
        pageManager.add_page(pages.ClientRegisterPage())
        pageManager.add_page(pages.EndPage('Registration complete'))

        return Wizard(self.jid, stateManager, pageManager)

class ClientUnregisterWizardFactory(object):
    """
    ClientUnregisterWizardFactory: Factory class for building a wizard for unregistering a client
    with a specific sub system.
    
    @ivar jid: The JID of the sender
    @type jid: L{jid.JID}
    
    """
    def __init__(self, jid, unregistration):
        self.jid = jid
        self.unregistration = unregistration
        
    def build(self):
        changer = sm.ClientRegisterStateChanger(self.unregistration) # can use the same state changer here as the closure is different
        stateManager = sm.StateManager(changer)

        pageManager = pm.PageManager()
        pageManager.add_page(pages.ClientUnregisterPage())
        pageManager.add_page(pages.EndPage('Unregistration complete'))

        return Wizard(self.jid, stateManager, pageManager)

        
def makeSubSystemCommands(xmenu, jid, handler, name, sub_top, cmds):
    xmenu.addSubMenu(
        entity=jid,
        nodeIdentifier=sub_top,
        parentNodeIdentifier=xmenu.top,
        category='automation',
        idType='command-list',
        name=name
        )

    for name, factory in cmds.iteritems():
        wizard = factory.build()
        handler = wizard.addCommand(sub_top, name, handler, xmenu)
    return handler


