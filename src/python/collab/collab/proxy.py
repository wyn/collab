# Copyright (c) Simon Parry.
# See LICENSE for details.

from twisted.internet import defer
from twisted.words.protocols.jabber.jid import JID
from wokkel import pubsub as ps
from zope.interface import implements, Interface

import collab
from collab import simulation as sim, wizards, pubsubRequestWithAffiliations as psaff
from collab.collabNode import CollabNode


class IAPIMixin(Interface):

    def api_register(jid):
        """
        Clients call this to register with the API and let the Proxy know who they are
        The proxy can then set up an appropriate comms channel which is returned
        to the client so that they can use that for communicating
        @ivar jid: The JID of the client
        @type jid: L{jid.JID}
        @return: name of pubsub channel to use for communicating
        """
        pass

    def api_unregister(jid):
        """
        Called when the client is finished with a proxy
        Use to release any resources aquired
        """
        pass
    
    def api_onGotStart(params, portfolio, nodename):
        pass

    def api_onGotStop(params):
        pass

    def api_broadcastProgress(params, progress):
        pass

    def api_broadcastResults(params, distributions):
        pass
    

class APIMixin(object):
    implements(IAPIMixin)

    def __init__(self, jid, psclient):
        self.jid = jid
        self.psclient = psclient
        self.runs = {} # run id to api node mapping
        self.clients = {} # jid to ps node
        
    def api_register(self, jid):
        # make new temp ps node, self.jid is the owner
        # then make jid a publisher and subscriber
        d = self.psclient.createNode(JID(collab.PUBSUB_NODE), sender=self.jid)
        def cb(new_node):
            # need some way of identifying these nodes if APIMixin gets restarted
            # e.g. use pubsub node tree and have an API folder?
            self.clients[jid] = new_node
            ds = []
            ds.append(psaff.makeSubscriptions(
                self.jid,
                new_node,
                set([ps.Subscription(
                    nodeIdentifier=None, subscriber=jid, state='subscribed'
                    )]),
                self.psclient.xmlstream
                ))
            ds.append(psaff.makeAffiliations(
                self.jid,
                new_node,
                dict({jid.full(): 'publisher'}),
                self.psclient.xmlstream
                ))
            
            def inner(data):
                return new_node

            def eb(err):
                return self.api_unregister(jid)
                
            l = defer.DeferredList(ds)
            l.addCallbacks(inner, eb)
            return l

        d.addCallback(cb)
        return d

    def api_unregister(self, jid):
        if jid not in self.clients:
            return

        node = self.clients[jid]
        d = self.psclient.deleteNode(JID(collab.PUBSUB_NODE), node, self.jid)
        def cb(data):
            del self.clients[jid]

        d.addCallbacks(cb, cb)
        return d
    
    def api_onGotStart(self, params, portfolio, nodename):
        pass

    def api_onGotStop(self, params):
        pass

    def api_broadcastProgress(self, params, progress):
        pass

    def api_broadcastResults(self, params, distributions):
        pass
    
    def _makeApiNode(self, nodename):
        apinode = nodes.ApiNode(self.jid, self)
        d = apinode.setConnection(nodename)
        def cb(data):
            return apinode

        return d
    
class CollabProxy(CollabNode, APIMixin):
    """
    CollabProxy: A proxy for running Collab commands
    
    @ivar jid: The JID identifier
    @type jid: L{JID}
    
    """
    
    def __init__(self, jid, name=None, errorNode=None, outputNode=None, inputNode=None, loopingLoadBalancer=None):
        CollabNode.__init__(
            self, jid, name, errorNode, outputNode, inputNode, loopingLoadBalancer
            )

        APIMixin.__init__(self, jid, self)

    def connectionInitialized(self):
        super(CollabProxy, self).connectionInitialized()
        
        self.lastHandler = wizards.makeSubSystemCommands(
            self.menu, self.jid, self.lastHandler, 'Analysis', 'mc_analysis',
            dict({
            'Register client': wizards.ClientRegisterWizardFactory(self.jid, self.api_register),
            'Unregister client': wizards.ClientUnregisterWizardFactory(self.jid, self.api_unregister),
            }))

    def onGotItem(self, item):
        """
        Process the given item and broadcast outcome
        Needs to respond to stop messages by collecting the answer together and then passing them on

        API calls need to be distinguished from subsystem messages
        
        """
        d = defer.Deferred()
        logs = sim.Logger()
        node = item.nodeIdentifier
        el = item.firstChildElement()
        params = sim.getParameters(el, logs)
        if not params:
            # not an item for this component
            d = defer.succeed(None)

        # API calls
        if params.cmd == 'stop':
            d = self.api_onGotStop(params)

        elif params.cmd == 'start':
            portfolio = port.getPortfolio(el, logs)
            d = self.api_onGotStart(params, portfolio, node)

        elif params.cmd == 'results':
            dists = sim.getDistributions(el, logs)
            d = self.api_broadcastResults(params, dists)

        elif params.cmd == 'info':
            progress = sim.getProgress(el, logs)
            if progress:
                d = self.api_broadcastProgress(params, progress)

        return d
    
    def api_onGotStart(self, params, portfolio, nodename):
        run_id = params.run_id
        if run_id not in self.runs:
            d = self._makeApiNode(nodename)
            def cb(apinode):
                self.runs[run_id] = apinode
                params.setCommand('start')
                sim = params.toElement()
                sim.addChild(portfolio.toElement())
                return self.outputNode.onOutput(data=sim)

            d.addCallback(cb)
            return d

    def api_onGotStop(self, params):
        run_id = params.run_id
        if run_id in self.runs:
            del self.runs[run_id]
            return self.broadcastStop(params)

    def api_broadcastProgress(self, params, progress):
        run_id = params.run_id
        if run_id in self.runs:
            apiNode = self.runs[run_id]
            params.setCommand('info')
            prog = params.toElement()
            prog.addChild(progress.toElement())
            return apiNode.onOutput(data=prog)

    def api_broadcastResults(self, params, distributions):
        run_id = params.run_id
        if run_id in self.runs:
            params.setCommand('results')
            res = params.toElement()
            res.addChild(distributions.toElement())
            return apiNode.onOutput(data=res)

    
