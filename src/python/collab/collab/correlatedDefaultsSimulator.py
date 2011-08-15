# Copyright (c) Simon Parry.
# See LICENSE for details.

import copy
from collections import defaultdict

from twisted.internet import defer, task
from twisted.python import log

import collab
from collab import simulation as sim, portfolio as port, copulas
from collab.collabNode import CollabNode


class CorrelatedDefaultsSimulator(CollabNode):
    """
    Performs a multifactor, single step, Gaussian copula simulation
    TODO need to check the defaults node exists before publishing to it?

    Listens for start/stop stanzas on the simulation node
    Broadcasts results onto defaults node
    """
    def __init__(self, jid, name=None, errorNode=None, outputNode=None, inputNode=None, loopingLoadBalancer=None, broadcast_freq = collab.DEFAULT_BROADCAST_FREQ, max_runs = collab.DEFAULT_MAX_RUNS, simFactory = None):
        super(CorrelatedDefaultsSimulator, self).__init__(
            jid, name, errorNode, outputNode, inputNode, loopingLoadBalancer
            )

        # dict of run_id to CooperativeTasks
        self.broadcast_freq = broadcast_freq
        self.max_runs = max_runs
        self.tasks = {}
        self.simulatorFactory = simFactory or copulas.theSimulatorFactory

    def connectionInitialized(self):
        super(CorrelatedDefaultsSimulator, self).connectionInitialized()

    def onGotItem(self, item):
        logger = sim.Logger()
        params = sim.getParameters(item, logger)
        d = defer.succeed(None)
        if not params:
            log.msg('cannot find run id')

        elif params.cmd == 'start':
            if params.run_id not in self.tasks:
                self.tasks[params.run_id] = self.coop.cooperate(self.onGotStartSimulation(params, item, logger))

        elif params.cmd == 'stop':
            d = self.onGotStoppedSimulation(params)

        return d

    def onGotStartSimulation(self, params, item, logger, chunk=100):
        # get the deferred, add an errback to it and then stick in the cooperator
        log.msg('sim start', params.run_id)
        portfolio = port.getPortfolio(item, logger)
        if not portfolio:
            yield self.broadcastLogs(logger, params)
        else:
            # prep copula
            try:
                simulator = self.simulatorFactory['sparse'](portfolio)
            except Exception as e:
                yield self._errback(e, logger, params)
            else:
                # run a chunk, yielding
                defaults = defaultdict(int)
                for count in xrange(0, self.max_runs, chunk):
                    try:
                        simulator.copula(chunk/10, 10, defaults)
                        log.msg('%s done %i' % (params.run_id, count))
                    except Exception as e:
                        yield self._errback(e, logger, params)
                    else:
                        yield defer.succeed(None)

                    if count > 0 and count%self.broadcast_freq == 0:
                        distributions = sim.Distributions()
                        distributions.combine(collab.DEFAULTS_EL, copy.deepcopy(defaults))
                        # broadcast out results, yield
                        log.msg(
                            '%s: broadcasting results so far [%s / %s]' % (params.run_id, count, params.number_runs)
                            )
                        prog = sim.Progress(self.broadcast_freq)
                        d = self.broadcastResults(params, prog, distributions)
                        d.addErrback(self._errback, logger, params)
                        yield d
                        defaults.clear()


    def onGotStoppedSimulation(self, params):
        log.msg('stopping task', params.run_id)
        if params.run_id not in self.tasks:
            return defer.succeed(None)
        else:
            log.msg('task still running', params.run_id)
            t = self.tasks[params.run_id]
            try:
                t.stop()
                log.msg('stopped task', params.run_id)
            except task.TaskDone as e1:
                log.msg('Task %s already done' % params.run_id)
            except task.TaskStopped as e2:
                log.msg('Task %s already stopped' % params.run_id)
            except task.TaskFailed as e3:
                log.msg('Task %s already failed' % params.run_id)
            except task.TaskFinished as e4:
                log.msg('Task %s already finished' % params.run_id)

            del self.tasks[params.run_id]
            log.msg('deleted task', params.run_id)

            return self.broadcastStop(params)

    def broadcastResults(self, params, progress, distributions):
        """
        pubsub publish to the defaults node that some output is ready to process
        for the given run and trial
        """
        params.setCommand('results')
        el = params.toElement()
        el.addChild(distributions.toElement())
        el.addChild(progress.toElement())

        return self.outputNode.onOutput(data=el)
