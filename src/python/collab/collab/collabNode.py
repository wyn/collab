# Copyright (c) Simon Parry.
# See LICENSE for details.

from datetime import datetime

from twisted.internet import defer, task
from twisted.python import log
from wokkel import pubsub, disco
from wokkel.iwokkel import IDisco
from zope.interface import implements

import collab
from collab import xmppMenuSystem as xmenu, xmppCommandSystem as xcmd, wizards, nodes, simulation as sim


class CollabNode(pubsub.PubSubClient):
    """
    Base class for Collab PS clients
    """
    implements(IDisco)
    
    def __init__(self, jid, name=None, errorNode=None, outputNode=None, inputNode=None, loopingLoadBalancer=None):
        super(CollabNode, self).__init__()
        self.jid = jid
        self.name = name or self.jid.full()
        self.errorNode = errorNode or nodes.PSErrorNode(jid, self)
        self.outputNode = outputNode or nodes.PSOutputNode(jid, self)
        self.inputNode = inputNode or nodes.PSInputNode(jid, self)
        ntlb = nodes.NonTrippingLoadBalancer()
        self.loopingLoadBalancer = loopingLoadBalancer or task.LoopingCall(self._checkLoading, ntlb)

        self.overloaded = False
        self.inputs = set()

        self.menu = xmenu.XmppMenuSystem(
            entity=jid,
            nodeIdentifier='%s_node_manager' % jid,
            name=self.name
            )

        self.commandHandler = xcmd.PassThroughHandler()
        self.lastHandler = None
        self.coop = task.Cooperator()
        self.discoClient = disco.DiscoClientProtocol()

    def setHandlerParent(self, parent):
        super(CollabNode, self).setHandlerParent(parent)
        self.discoClient.setHandlerParent(parent)
        
    def itemsReceived(self, event):

        def parseItems(event):
            for item in event.items:
                log.msg('got item: %s' % item.toXml())
                d = self.onGotItem(item)
                d.addErrback(self._errback)
                yield d

        log.msg('listening ...')
        # if we return the coiterator deferred then testing is easier
        return self.coop.coiterate(parseItems(event))

    def onGotItem(self, item):
        """
        Processes one L{Element} item and returns a L{defer.Deferred}
        Overridden in derived classes
        """
        pass
        
    def connectionInitialized(self):
        super(CollabNode, self).connectionInitialized()
        log.msg('connection done')

        # make it able to handle ad-hoc commands
        self.xmlstream.addObserver(collab.COMMAND_SET, self.handleCommand)

        # communications sub menus - want connections to all be init so doing this here
        self.lastHandler = wizards.makeSubSystemCommands(
            self.menu, self.jid, self.commandHandler, 'Input/Output/Errors', 'comm_inputs',
            dict({
            'View': wizards.ViewCollabNodeWizardFactory(self.jid, self.inputNode, self.outputNode, self.errorNode),
            }))

        self.lastHandler = wizards.makeSubSystemCommands(
            self.menu, self.jid, self.lastHandler, 'Load Balancer', 'load_balancer',
            dict({
            'Configure': wizards.ConfigureCollabLoadBalancingWizardFactory(self.jid, self.loopingLoadBalancer)
            }))

        #set load balancer looping call every x second
        if not self.loopingLoadBalancer.running:
            d = self.loopingLoadBalancer.start(collab.DEFAULT_LOAD_BALANCER_FREQ)
            d.addErrback(self._errback)
            return d
        
        return defer.succeed(None)
            
    def getDiscoInfo(self, requestor, target, nodeIdentifier=''):
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

    def handleCommand(self, iq):
        d = self.commandHandler.process_iq(iq)
        d.addCallback(self.xmlstream.send)
        # TODO - error handling
        return d
        

    def _checkLoading(self, loadBalancer):
        """
        To allow a looping call, check load every so often
        """
        
        env = None

        if not self.overloaded:
            def onOverload(inputs):
                self.inputs = inputs
                self.overloaded = True

            def eb(err):
                return self._errback(err)

            # we are not overloaded but now the balancer is so unhook for a bit
            if loadBalancer.overloaded(env):
                d = loadBalancer.suspendAll(self.inputNode)
                d.addCallback(onOverload)
                d.addErrback(eb)
                return d
        else:
            def eb(err, inputs):
                self.inputs = inputs
                self.overloaded = True
                return self._errback(err)

            # we were overloaded but the balancer is not anymore so hook back in
            if not loadBalancer.overloaded(env):
                self.overloaded = False
                inputs, self.inputs = self.inputs, set()
                d = loadBalancer.reloadAll(self.inputNode, inputs)
                d.addErrback(eb, inputs)
                return d

        return defer.succeed(None)

    def broadcastStop(self, params):
        """
        pubsub publish to the simulations node to stop the given run
        """
        log.msg('stopping', params.run_id)
        elapsed = datetime.now() - params.timestamp
        log.msg('%s: elapsed %s' % (params.run_id, elapsed))

        params.setCommand('stop')
        return self.outputNode.onOutput(data=params.toElement())

    def broadcastLogs(self, logs, params=None):
        """
        pubsub publish to the errors node
        """
        if not params:
            params = sim.Parameters()
        params.setCommand('info')
        el = params.toElement()
        el.addChild(logs.toElement())
        return self.errorNode.onError(error=el)

    def _errback(self, err, logs=None, params=None):
        logs = logs or sim.Logger()
        logs.addLog(collab.ERROR_EL, str(err))
        d = self.broadcastLogs(logs, params)
        def eb(err):
            log.msg(err)

        d.addErrback(eb)
        return d
        
