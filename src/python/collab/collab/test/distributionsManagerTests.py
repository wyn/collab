# Copyright (c) Simon Parry.
# See LICENSE for details.

from collections import defaultdict

from mock import Mock
from twisted.internet import defer, task
from twisted.trial import unittest
from twisted.words.protocols.jabber import jid
from twisted.words.xish.domish import Element
from wokkel import pubsub

from collab import simulation as sim
from collab.distributionsManager import DistributionsManager
from collab.test import utils


testjid = jid.JID('test@master.local')

class Basic(object):
    def __init__(self):
        self.coop = None

    def itemsReceived(self, n):
        def parseItems(n):
            for i in xrange(n):
                yield self.prnt(i)
        return self.coop.coiterate(parseItems(n))

    def prnt(self, i):
        print 'this is ', i
        return defer.Deferred() #will hang unless mocked away


class DistributionsManagerTests(unittest.TestCase):
    """
    DistributionsManagerTests: Tests for the L{DistributionsManager} class
    
    """
    
    timeout = 2
    
    def setUp(self):
        self.dm = DistributionsManager(testjid)
        self.sch = utils.ClockScheduler(task.Clock())
        self.dm.coop = task.Cooperator(scheduler=self.sch.callLater)
            
    def tearDown(self):
    	pass

    def test_clock(self):
        b = Basic()
        sch = utils.ClockScheduler(task.Clock())
        b.coop = task.Cooperator(scheduler=sch.callLater)
        b.prnt = Mock(return_value=defer.succeed('lush'))

        d = b.itemsReceived(10)
        def check(data):
            self.assertEquals(b.prnt.call_count, 10)
            
        d.addCallback(check)
        # the coiterator pauses the b.prnt generator each time it yields because it's yielding deferreds,
        # even though they are fired already.  Therefore you need to pump the clock 10 times.
        # for testing they need to be defer.succeed though, to allow them to complete
        sch.clock.pump([i*0.1 for i in xrange(10)])
        return d

    def test_onGotItem_noParams(self):
        self.dm.onGotDistribution = Mock()
        self.dm.onGotStoppedSimulation = Mock()

        item = Element((pubsub.NS_PUBSUB_EVENT, 'item'))
        item['id'] = str(1)
        item.addElement('stuff', content='nothing to do with parameters')

        d = self.dm.onGotItem(item)
        def check(data):
            self.assertTrue(data is None)
            self.assertFalse(self.dm.onGotDistribution.called)
            self.assertFalse(self.dm.onGotStoppedSimulation.called)

        d.addCallback(check)
        return d

    def test_onGotItem_results(self):
        self.dm.onGotDistribution = Mock(side_effect=utils.good_side_effect('lush'))
        self.dm.onGotStoppedSimulation = Mock()

        item = Element((pubsub.NS_PUBSUB_EVENT, 'item'))
        item['id'] = str(1)
        params = sim.Parameters(run_id='1', cmd='results')
        params_el = params.toElement()
        params_el.addChild(sim.Progress(200).toElement())
        params_el.addChild(sim.Distributions().toElement())
        item.addChild(params_el)
        d = self.dm.onGotItem(item)
        def check(data):
            self.assertEquals(data, 'lush')
            self.assertEquals(self.dm.onGotDistribution.call_count, 1)
            self.assertFalse(self.dm.onGotStoppedSimulation.called)

        d.addCallback(check)
        return d

    def test_onGotItem_stop(self):
        self.dm.onGotStoppedSimulation = Mock(side_effect=utils.good_side_effect('lush'))
        self.dm.onGotDistribution = Mock()

        item = Element((pubsub.NS_PUBSUB_EVENT, 'item'))
        item['id'] = str(1)
        params = sim.Parameters(run_id='1', cmd='stop')
        params_el = params.toElement()
        params_el.addChild(sim.Progress(200).toElement())
        params_el.addChild(sim.Distributions().toElement())
        item.addChild(params_el)
        d = self.dm.onGotItem(item)
        def check(data):
            self.assertEquals(data, 'lush')
            self.assertEquals(self.dm.onGotStoppedSimulation.call_count, 1)
            self.assertFalse(self.dm.onGotDistribution.called)

        d.addCallback(check)
        return d

    def test_onGotDistribution_noDistribution(self):
        self.dm.broadcastLogs = Mock(side_effect=utils.good_side_effect('lush'))
        self.dm.handleDistribution = Mock()
        self.dm._errback = Mock(side_effect=utils.good_side_effect('err logged'))

        item = Element((pubsub.NS_PUBSUB_EVENT, 'item'))
        item['id'] = str(1)
        params = sim.Parameters(run_id='1', cmd='results')
        params_el = params.toElement()
        params_el.addChild(sim.Progress(200).toElement())
        item.addChild(params_el)

        lg = sim.Logger()
        d = self.dm.onGotDistribution(params, item, lg)

        def check(data):
            self.assertFalse(self.dm.handleDistribution.called)
            self.assertEquals(self.dm.broadcastLogs.call_count, 1)
            self.assertFalse(self.dm._errback.called)

        d.addCallback(check)
        self.sch.clock.pump([1,1,1])
        return d

    def test_onGotDistribution_noDistribution_badBroadcast(self):
        self.dm.broadcastLogs = Mock(side_effect=utils.bad_side_effect(Exception('%s: groan' % self.__class__)))
        self.dm.handleDistribution = Mock()
        self.dm._errback = Mock(side_effect=utils.good_side_effect('err logged'))

        item = Element((pubsub.NS_PUBSUB_EVENT, 'item'))
        item['id'] = str(1)
        params = sim.Parameters(run_id='1', cmd='results')
        params_el = params.toElement()
        params_el.addChild(sim.Progress(200).toElement())
        item.addChild(params_el)

        lg = sim.Logger()
        d = self.dm.onGotDistribution(params, item, lg)

        def check(data):
            self.assertFalse(self.dm.handleDistribution.called)
            self.assertEquals(self.dm.broadcastLogs.call_count, 1)
            self.assertEquals(self.dm._errback.call_count, 1)

        d.addCallback(check)
        self.sch.clock.pump([1,1,1])
        return d

    def test_onGotDistribution_noProgress(self):
        self.dm.broadcastLogs = Mock(side_effect=utils.good_side_effect('lush'))
        self.dm.handleDistribution = Mock()
        self.dm._errback = Mock(side_effect=utils.good_side_effect('err logged'))

        item = Element((pubsub.NS_PUBSUB_EVENT, 'item'))
        item['id'] = str(1)
        params = sim.Parameters(run_id='1', cmd='results')
        params_el = params.toElement()
        params_el.addChild(sim.Distributions().toElement())
        item.addChild(params_el)

        lg = sim.Logger()
        d = self.dm.onGotDistribution(params, item, lg)

        def check(data):
            self.assertFalse(self.dm.handleDistribution.called)
            self.assertEquals(self.dm.broadcastLogs.call_count, 1)
            self.assertFalse(self.dm._errback.called)

        d.addCallback(check)
        self.sch.clock.pump([1,1,1])
        return d

    def test_onGotDistribution_noProgress_badBroadcast(self):
        self.dm.broadcastLogs = Mock(side_effect=utils.bad_side_effect(Exception('%s: groan' % self.__class__)))
        self.dm.handleDistribution = Mock()
        self.dm._errback = Mock(side_effect=utils.good_side_effect('err logged'))

        item = Element((pubsub.NS_PUBSUB_EVENT, 'item'))
        item['id'] = str(1)
        params = sim.Parameters(run_id='1', cmd='results')
        params_el = params.toElement()
        params_el.addChild(sim.Distributions().toElement())
        item.addChild(params_el)

        lg = sim.Logger()
        d = self.dm.onGotDistribution(params, item, lg)

        def check(data):
            self.assertFalse(self.dm.handleDistribution.called)
            self.assertEquals(self.dm.broadcastLogs.call_count, 1)
            self.assertEquals(self.dm._errback.call_count, 1)

        d.addCallback(check)
        self.sch.clock.pump([1,1,1])
        return d

    def test_onGotDistribution(self):
        self.dm.broadcastLogs = Mock()
        self.dm.handleDistribution = Mock(side_effect=utils.good_side_effect('lush'))
        self.dm._errback = Mock(side_effect=utils.good_side_effect('err logged'))

        item = Element((pubsub.NS_PUBSUB_EVENT, 'item'))
        item['id'] = str(1)
        params = sim.Parameters(run_id='1', cmd='results')
        params_el = params.toElement()
        progress = sim.Progress(200)
        params_el.addChild(progress.toElement())
        dist = sim.Distributions()
        hist = defaultdict(int)
        hist[1] = 1
        hist[2] = 2
        dist.combine('a', hist)
        params_el.addChild(dist.toElement())
        item.addChild(params_el)

        lg = sim.Logger()
        d = self.dm.onGotDistribution(params, item, lg)

        def check(data):
            self.assertFalse(self.dm.broadcastLogs.called)
            self.assertEquals(self.dm.handleDistribution.call_count, 1)
            self.assertFalse(self.dm._errback.called)

        d.addCallback(check)
        self.sch.clock.pump([1,1,1])
        return d

    def test_onGotStoppedSimulation(self):
        params = sim.Parameters(run_id='1', cmd='stop')
        self.dm.distributions[1] = sim.Distributions()
        self.dm.number_checks[1] = 0
        self.dm.stopped_runs.add(1)

        d = self.dm.onGotStoppedSimulation(params)
        def check(data):
            self.assertFalse('1' in self.dm.distributions)
            self.assertFalse('1' in self.dm.number_checks)
            self.assertFalse('1' in self.dm.stopped_runs)

        d.addCallback(check)
        return d

    def test_onGotStoppedSimulation_noneThere(self):
        params = sim.Parameters(run_id='1', cmd='stop')

        d = self.dm.onGotStoppedSimulation(params)
        def check(data):
            self.assertFalse(1 in self.dm.distributions)
            self.assertFalse(1 in self.dm.number_checks)
            self.assertFalse(1 in self.dm.stopped_runs)

        d.addCallback(check)
        return d

    def test_handleDistribution_combiningSameRunId(self):
        run_id = '1'
        name = 'name'

        old_dist = defaultdict(int)
        for i in xrange(10):
            old_dist[i] = i
        self.dm.distributions[run_id] = sim.Distributions(dict({name: old_dist}))

        params = sim.Parameters(run_id=run_id, cmd='results')

        new_dist = defaultdict(int)
        for i in xrange(10):
            new_dist[i] = i

        progress = sim.Progress(200)
        self.dm.checkStopCondition = Mock(return_value=False)
        self.dm.broadcastProgress = Mock(side_effect=utils.good_side_effect('lush'))
        self.dm._errback = Mock(side_effect=utils.good_side_effect('err handled'))

        d = self.dm.handleDistribution(params, name, new_dist, progress)
        def check(data):
            for k, v in self.dm.distributions[run_id].histograms[name].iteritems():
                #old_dist and new_dist should have combined by adding values
                self.assertEquals(v, 2*k)
            self.assertFalse(self.dm._errback.called)

        d.addCallback(check)
        self.sch.clock.pump([1,1,1])
        return d

    def test_handleDistribution_combiningNewRunId(self):
        name = 'name'

        old_dist = defaultdict(int)
        for i in xrange(10):
            old_dist[i] = i
        self.dm.distributions[1] = sim.Distributions(dict({name: old_dist}))

        params = sim.Parameters(run_id=2, cmd='results')

        new_dist = defaultdict(int)
        for i in xrange(10):
            new_dist[i] = i

        progress = sim.Progress(200)
        self.dm.checkStopCondition = Mock(return_value=False)
        self.dm.broadcastProgress = Mock(side_effect=utils.good_side_effect('lush'))
        self.dm._errback = Mock(side_effect=utils.good_side_effect('err handled'))

        d = self.dm.handleDistribution(params, name, new_dist, progress)
        def check(data):
            for run_id in xrange(1,2):
                for k, v in self.dm.distributions[run_id].histograms[name].iteritems():
                    #old_dist and new_dist should not have combined
                    self.assertEquals(v, k)
            self.assertFalse(self.dm._errback.called)

        d.addCallback(check)
        self.sch.clock.pump([1,1,1])
        return d

    def test_handleDistribution_notStopping(self):
        name = 'name'
        params = sim.Parameters(run_id='1', cmd='results')

        distribution = defaultdict(int)
        for i in xrange(10):
            distribution[i] = i

        progress = sim.Progress(200)
        self.dm.checkStopCondition = Mock(return_value=False)
        self.dm.broadcastResults = Mock()
        self.dm.broadcastStop = Mock()
        self.dm.broadcastProgress = Mock(side_effect=utils.good_side_effect('lush'))
        self.dm._errback = Mock(side_effect=utils.good_side_effect('err handled'))

        d = self.dm.handleDistribution(params, name, distribution, progress)
        def check(data):
            self.dm.checkStopCondition.assert_called_once_with(params, progress.runs)
            self.assertFalse(self.dm.broadcastResults.called)
            self.assertFalse(self.dm.broadcastStop.called)
            self.dm.broadcastProgress.assert_called_once_with(params, progress)

        d.addCallback(check)
        self.sch.clock.pump([1,1,1])
        return d

    def test_handleDistribution_stopping(self):
        name = 'name'
        run_id = '1'
        params = sim.Parameters(run_id=run_id, cmd='results')

        distribution = defaultdict(int)
        for i in xrange(10):
            distribution[i] = i

        progress = sim.Progress(200)
        self.dm.checkStopCondition = Mock(return_value=True)
        self.dm.broadcastResults = Mock(side_effect=utils.good_side_effect('lush'))
        self.dm.broadcastStop = Mock(side_effect=utils.good_side_effect('lush'))
        self.dm.broadcastProgress = Mock(side_effect=utils.good_side_effect('lush'))
        self.dm._errback = Mock(side_effect=utils.good_side_effect('err handled'))

        d = self.dm.handleDistribution(params, name, distribution, progress)
        def check(data):
            self.dm.checkStopCondition.assert_called_once_with(params, progress.runs)
            self.assertEquals(self.dm.broadcastResults.call_count, 1)
            self.assertEquals(self.dm.broadcastStop.call_count, 1)
            self.dm.broadcastProgress.assert_called_once_with(params, progress)
            self.assertTrue(run_id in self.dm.stopped_runs)
            self.assertFalse(self.dm._errback.called)

        d.addCallback(check)
        self.sch.clock.pump([1,1,1])
        return d

    def test_handleDistribution_stoppingButAlreadyStopped(self):
        name = 'name'
        run_id = '1'
        params = sim.Parameters(run_id=run_id, cmd='results')

        distribution = defaultdict(int)
        for i in xrange(10):
            distribution[i] = i

        progress = sim.Progress(200)
        self.dm.checkStopCondition = Mock(return_value=True)
        self.dm.broadcastResults = Mock(side_effect=utils.good_side_effect('lush'))
        self.dm.broadcastStop = Mock(side_effect=utils.good_side_effect('lush'))
        self.dm.broadcastProgress = Mock(side_effect=utils.good_side_effect('lush'))
        # already stopped
        self.dm.stopped_runs.add(run_id)
        self.dm._errback = Mock(side_effect=utils.good_side_effect('err handled'))

        d = self.dm.handleDistribution(params, name, distribution, progress)
        def check(data):
            self.dm.checkStopCondition.assert_called_once_with(params, progress.runs)
            self.assertFalse(self.dm.broadcastResults.called)
            self.assertFalse(self.dm.broadcastStop.called)
            self.dm.broadcastProgress.assert_called_once_with(params, progress)
            self.assertTrue(run_id in self.dm.stopped_runs)
            
        d.addCallback(check)
        self.sch.clock.pump([1,1,1])
        return d

    def test_handleDistribution_stoppingBadBroadcastResults(self):
        name = 'name'
        run_id = '1'
        params = sim.Parameters(run_id=run_id, cmd='results')

        distribution = defaultdict(int)
        for i in xrange(10):
            distribution[i] = i

        progress = sim.Progress(200)
        self.dm.checkStopCondition = Mock(return_value=True)
        self.dm.broadcastResults = Mock(side_effect=utils.bad_side_effect(ValueError('%s: arrrgh' % self.__class__)))
        self.dm.broadcastStop = Mock(side_effect=utils.good_side_effect('lush'))
        self.dm.broadcastProgress = Mock(side_effect=utils.good_side_effect('lush'))
        self.dm._errback = Mock(side_effect=utils.good_side_effect('err handled'))

        d = self.dm.handleDistribution(params, name, distribution, progress)
        def check(data):
            self.dm.checkStopCondition.assert_called_once_with(params, progress.runs)
            self.assertEquals(self.dm.broadcastResults.call_count, 1)
            self.assertEquals(self.dm.broadcastStop.call_count, 1)
            self.dm.broadcastProgress.assert_called_once_with(params, progress)
            self.assertFalse(run_id in self.dm.stopped_runs)
            self.assertTrue(self.dm._errback.called)

        d.addCallback(check)
        self.sch.clock.pump([1,1,1])
        return d

    def test_handleDistribution_stoppingBadBroadcastStop(self):
        name = 'name'
        run_id = '1'
        params = sim.Parameters(run_id=run_id, cmd='results')

        distribution = defaultdict(int)
        for i in xrange(10):
            distribution[i] = i

        progress = sim.Progress(200)
        self.dm.checkStopCondition = Mock(return_value=True)
        self.dm.broadcastResults = Mock(side_effect=utils.good_side_effect('lush'))
        self.dm.broadcastStop = Mock(side_effect=utils.bad_side_effect(ValueError('%s: arrrgh' % self.__class__)))
        self.dm.broadcastProgress = Mock(side_effect=utils.good_side_effect('lush'))
        self.dm._errback = Mock(side_effect=utils.good_side_effect('err handled'))

        d = self.dm.handleDistribution(params, name, distribution, progress)
        def check(data):
            self.dm.checkStopCondition.assert_called_once_with(params, progress.runs)
            self.assertEquals(self.dm.broadcastResults.call_count, 1)
            self.assertEquals(self.dm.broadcastStop.call_count, 1)
            self.dm.broadcastProgress.assert_called_once_with(params, progress)
            self.assertFalse(run_id in self.dm.stopped_runs)
            self.assertTrue(self.dm._errback.called)
            
        d.addCallback(check)
        self.sch.clock.pump([1,1,1])
        return d

    def test_checkStopCondition_runsAlreadyThereAndStop(self):
        run_id = '1'
        params = sim.Parameters(run_id=run_id, number_runs=200, cmd='results')
        self.dm.number_checks[run_id] = 100
        self.assertTrue(self.dm.checkStopCondition(params, 100))

    def test_checkStopCondition_runsAlreadyThereAndContinue(self):
        run_id = '1'
        params = sim.Parameters(run_id=run_id, number_runs=200, cmd='results')
        self.dm.number_checks[run_id] = 100
        self.assertFalse(self.dm.checkStopCondition(params, 99))

    def test_checkStopCondition_runsNotThere(self):
        run_id = '1'
        params = sim.Parameters(run_id=run_id, number_runs=200, cmd='results')
        self.assertFalse(self.dm.checkStopCondition(params, 99))
        self.assertEquals(self.dm.number_checks[run_id], 99)
        
        
