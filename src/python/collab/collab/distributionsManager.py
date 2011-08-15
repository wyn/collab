# Copyright (c) Simon Parry.
# See LICENSE for details.

#manages the distributions for gc runs
from collections import defaultdict

from twisted.internet import defer
from twisted.python import log

from collab import simulation as sim
from collab.collabNode import CollabNode


class DistributionsManager(CollabNode):
    """
    Manages the distributions, collates and checks stopping condition
    """
    def __init__(self, jid, name=None, errorNode=None, outputNode=None, inputNode=None, loopingLoadBalancer=None):
        super(DistributionsManager, self).__init__(
            jid, name, errorNode, outputNode, inputNode, loopingLoadBalancer
            )

        self.distributions = defaultdict(sim.Distributions)

        #to make sure this will stop eventually
        self.number_checks = defaultdict(int)

        #to prevent the handler from spewing loads of extra stop commands
        #set of run_ids indicating ones that have already been stopped
        self.stopped_runs = set()
        
    def connectionInitialized(self):
        super(DistributionsManager, self).connectionInitialized()

    def onGotItem(self, item):
        logger = sim.Logger()
        params = sim.getParameters(item, logger)
        if not params:
            log.msg('cannot find run id')
            return defer.succeed(None)

        elif params.cmd == 'results':
            return self.onGotDistribution(params, item, logger)
        elif params.cmd == 'stop':
            return self.onGotStoppedSimulation(params)
    
    def onGotDistribution(self, params, item, logger):
        dists = sim.getDistributions(item, logger)
        progress = sim.getProgress(item, logger)

        def gen():
            # want to lock down any errors raised inside this as it will be used in a L{task.CooperativeTask}
            if not (progress and dists):
                d = self.broadcastLogs(logger, params)
                d.addErrback(self._errback, logger, params)
                yield d
            else:
                for name, dist in dists.histograms.iteritems():
                    d = self.handleDistribution(params, name, dist, progress)
                    d.addErrback(self._errback, logger, params)
                    yield d

        return self.coop.coiterate(gen())

    def onGotStoppedSimulation(self, params):
        if params.run_id in self.distributions:
            del self.distributions[params.run_id]

        if params.run_id in self.number_checks:
            del self.number_checks[params.run_id]
            
        if params.run_id in self.stopped_runs:
            self.stopped_runs.remove(params.run_id)

        return defer.succeed(None)
                
    def handleDistribution(self, params, dist_name, distribution, progress):
        dist = self.distributions[params.run_id]
        dist.combine(name=dist_name, dist=distribution)

        def gen():
            # want to lock down any errors raised inside this as it will be used in a L{task.CooperativeTask}
            # also need to know that broadcasting stop and results worked or not
            if self.checkStopCondition(params, progress.runs) and params.run_id not in self.stopped_runs:
                log.msg('%s: stopping' % params.run_id)
                self.stopped_runs.add(params.run_id)
                d1 = self.broadcastResults(params, dist)
                d2 = self.broadcastStop(params)
                def eb(err):
                    if params.run_id in self.stopped_runs:
                        self.stopped_runs.remove(params.run_id)
                    return self._errback(err, params=params)

                d1.addErrback(eb)
                d2.addErrback(eb)
                yield d1
                yield d2

            d = self.broadcastProgress(params, progress)
            d.addErrback(self._errback, params=params)
            yield d
        
        return self.coop.coiterate(gen())

    def checkStopCondition(self, params, runs_completed):
        """
        Check number of runs completed
        """
        self.number_checks[params.run_id] += runs_completed
        log.msg('%s: progress [%s / %s]' % (params.run_id, self.number_checks[params.run_id], params.number_runs))
        return self.number_checks[params.run_id] >= params.number_runs
    
    def broadcastResults(self, params, distributions):
        params.setCommand('results')
        el = params.toElement()
        el.addChild(distributions.toElement())
        return self.outputNode.onOutput(data=el)

    def broadcastProgress(self, params, progress):
        params.setCommand('info')
        el = params.toElement()
        el.addChild(progress.toElement())
        return self.outputNode.onOutput(data=el)
