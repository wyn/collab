# Copyright (c) Simon Parry.
# See LICENSE for details.

from twisted.internet import defer, task
from twisted.python import log
from twisted.words.protocols.jabber import jid
from wokkel import pubsub
from zope.interface import implements

import collab
from collab import inodes, pubsubRequestWithAffiliations as psaff


LOG_CHANNEL_NAME = 'log'

class PSInputNode(object):
    """
    This input node receives input by subscribing to XMPP pubsub nodes
    """
    implements(inodes.IInputNode)

    def __init__(self, jid, psclient):
        self.jid = jid
        self.psclient = psclient
        
    def inputChannels(self):
        """
        Returns a list of the currently set input channels
        """
        d_subs = psaff.getSubscriptionsForJid(self.jid, self.psclient.xmlstream)
        def getNodes(subs):
            return [s.nodeIdentifier for s in subs]
        d_subs.addCallback(getNodes)
        return d_subs

    def addInput(self, input_ch):
        """
        Adds a new input channel if necessary
        """
        d_inputs = self.inputChannels()
        def subscribe(inputs):
            # try to subscribe to upstream nodes
            if input_ch in inputs:
                return defer.succeed(None)

            log.msg('trying to subscribe to [%s] channel' % input_ch)
            d = self.psclient.subscribe(
                service=jid.JID(collab.PUBSUB_NODE),
                nodeIdentifier=input_ch,
                subscriber=self.jid
                )

            return d
        
        d_inputs.addCallback(subscribe)
        return d_inputs

    def removeInput(self, input_ch):
        """
        removes the given input channel
        """
        d_inputs = self.inputChannels()
        def unsubscribe(inputs):
            if input_ch not in inputs:
                return defer.succeed(None)

            log.msg('trying to unsubscribe from [%s] channel' % input_ch)
            d = self.psclient.unsubscribe(
                service=jid.JID(collab.PUBSUB_NODE),
                nodeIdentifier=input_ch,
                subscriber=self.jid
                )

            return d

        d_inputs.addCallback(unsubscribe)
        return d_inputs

    def canProcessInputSchema(self, schema):
        """
        Returns whether this can process the given schema
        """
        return True

class PSOutputNode(object):
    """
    This output node outputs data by publishing to XMPP pubsub nodes
    """
    implements(inodes.IOutputNode)

    def __init__(self, jid, psclient):
        self.jid = jid
        self.psclient = psclient
        self.coop = task.Cooperator()
        
    def outputChannels(self):
        """
        Returns the output channels this thing writes to
        """
        out_nodes = [LOG_CHANNEL_NAME]
        d_affs = psaff.getAffiliationsForJid(self.jid, self.psclient.xmlstream)
        def append(affs):
            [out_nodes.append(node) for node, aff in affs.iteritems() if aff == 'publisher' and 'error' not in node]

            return out_nodes
        
        d_affs.addCallback(append)
        return d_affs

    def outputSchema(self):
        """
        Returns some sort of description of the types of output produced
        """
        pass

    def onOutput(self, data):
        """
        Called when there is output to send
        """
        d_outputs = self.outputChannels()
        def process(outputs):
            def gen():
                for output_ch in outputs:
                    if output_ch == LOG_CHANNEL_NAME:
                        yield defer.succeed(log.msg(data.toXml()))
                    else:
                        yield self.psclient.publish(
                            service=jid.JID(collab.PUBSUB_NODE),
                            nodeIdentifier=output_ch,
                            items=[pubsub.Item(payload=data)],
                            sender=self.jid
                            )
                        
            return self.coop.coiterate(gen())

        d_outputs.addCallback(process)
        return d_outputs

    
class PSErrorNode(object):
    """
    Error output by publishing to a XMPP pubsub node
    """
    implements(inodes.IErrorNode)

    def __init__(self, jid, psclient):
        self.jid = jid
        self.psclient = psclient
        self.coop = task.Cooperator()
        
    def errorChannels(self):
        """
        Returns the one output channel this thing writes to
        """
        err_nodes = [LOG_CHANNEL_NAME]
        d_affs = psaff.getAffiliationsForJid(self.jid, self.psclient.xmlstream)
        def append(affs):
            [err_nodes.append(node) for node, aff in affs.iteritems() if aff == 'publisher' and 'error' in node]

            return err_nodes
        
        d_affs.addCallback(append)
        return d_affs

    def onError(self, error):
        """
        Called when an error occurs
        """
        d_error_chs = self.errorChannels()
        def process(error_chs):
            def gen():
                for error_ch in error_chs:
                    if error_ch == LOG_CHANNEL_NAME:
                        yield defer.succeed(log.msg(error.toXml()))
                    else:
                        yield self.psclient.publish(
                            service=jid.JID(collab.PUBSUB_NODE),
                            nodeIdentifier=error_ch,
                            items=[pubsub.Item(payload=error)],
                            sender=self.jid
                            )

            return self.coop.coiterate(gen())
        
        d_error_chs.addCallback(process)
        return d_error_chs


class NonTrippingLoadBalancer(object):
    """
    This load balancer never overloads, always returns false
    Use for components that always need to be connected (warning they still may actually overload)
    """
    implements(inodes.ILoadBalancer)

    def __init__(self):
        self.coop = task.Cooperator()

    def overloaded(self, environment):
        """
        Given the environment returns whether its overloaded or not
        """
        return False

    def suspendAll(self, input_node):
        """
        Suspends as much input as poss, returns the input channels suspended
        """
        d_old_inputs = input_node.inputChannels()
        def removeInputs(old_inputs):
            ret = set(old_inputs)

            def gen():
                for i in old_inputs:
                    d = input_node.removeInput(i)
                    def eb(err):
                        log.msg(err)
                        ret.remove(i)

                    d.addErrback(eb)
                    yield d

            d = self.coop.coiterate(gen())
            d.addCallback(lambda _: ret)
            return d

        d_old_inputs.addCallback(removeInputs)
        return d_old_inputs

    def reloadAll(self, input_node, old_inputs):
        """
        Reload all input, returns the inputs that were successfully added
        """
        successes = set(old_inputs)

        def gen():
            for i in old_inputs:
                d = input_node.addInput(i)
                def eb(err):
                    log.msg(err)
                    successes.remove(i)

                d.addErrback(eb)
                yield d

        d = self.coop.coiterate(gen())
        d.addCallback(lambda _: successes)
        return d

class ApiNode(object):
    """
    API Nodes are used to provide an API to a collab subsystem
    e.g. the VaR subsystem needs start(portfolio), cancel(run_id) commands
    and needs to receive progress(run_id), result(run_id) info
    
    API nodes are given to proxy collab nodes to allow directed comms with one or more clients
    They collect together input, output and error nodes all based on the same PS channel.
    The various clients are responsible for creating that PS channel as when they need to.
    This should allow for future extensions into MUC based shared work
    
    """

    def __init__(self, jid, psclient):
        self.jid = jid
        self.psclient = psclient
        self.input = None
        self.output = None
        self.error = None

    def setConnection(self, node):
        self.input = PSInputNode(self.jid, self.psclient)
        self.output = PSOutputNode(self.jid, self.psclient)
        self.error = PSErrorNode(self.jid, self.psclient)

        return self.input.addInput(node)

    def onOutput(self, data):
        return self.output.onOutput(data)

    def onError(self, data):
        return self.error.onError(data)
