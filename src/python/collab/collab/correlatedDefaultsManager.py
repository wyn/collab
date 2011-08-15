# Copyright (c) Simon Parry.
# See LICENSE for details.

from twisted.internet import defer
from twisted.python import log

import collab
from collab import simulation as sim, portfolio as port
from collab.collabNode import CollabNode


def getRunId(item, logs):
    """
    Tries to get the run ID
    """
    try:
        return item[collab.ID_EL]
    except KeyError as e:
        logs.addLog(collab.ERROR_EL, 'Cannot parse run ID: %s' % item.toXml())


class CorrelatedDefaultsManager(CollabNode):
    """
    Entry point for correlated defaults modelling sub system
    """
    
    def __init__(self, jid, name=None, errorNode=None, outputNode=None, inputNode=None, loopingLoadBalancer=None):
        super(CorrelatedDefaultsManager, self).__init__(
            jid, name, errorNode, outputNode, inputNode, loopingLoadBalancer
            )

    def connectionInitialized(self):
        super(CorrelatedDefaultsManager, self).connectionInitialized()
        
    def onGotItem(self, item):
        """
        Process the given item and broadcast outcome
        Note that item can either be a stop command or a start command not both
        errors get sent to the logger node and no further processing is done
        """
        d = defer.Deferred()
        logs = sim.Logger()
        el = item.firstChildElement()
        params = sim.getParameters(el, logs)
        if not params:
            # not an item for this component
            d = defer.succeed(None)

        elif params.cmd == 'stop':
            d = self.broadcastStop(params)
        
        elif params.cmd == 'start':
            # if they have requested a portfolio run
            # they should have provided an ID and output location
            params.run_id = getRunId(item, logs)
            portfolio = port.getPortfolio(el, logs)
            if logs.hasSeverity(collab.ERROR_EL):
                d = self.broadcastLogs(logs, params)
            else:
                # broadcast this one
                log.msg('Portfolio is valid, send on to be processed')
                d = self.broadcastStart(params, portfolio)

        return d

    def broadcastStart(self, params, portfolio):
        """
        pubsub publish to the simulations node that a simulation is required
        for the given run and portfolio
        """
        params.setCommand('start')
        sim = params.toElement()
        sim.addChild(portfolio.toElement())
        return self.outputNode.onOutput(data=sim)
