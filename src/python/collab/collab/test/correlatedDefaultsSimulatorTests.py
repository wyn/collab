# Copyright (c) Simon Parry.
# See LICENSE for details.

from mock import Mock, MagicMock
from twisted.internet import task
from twisted.trial import unittest
from twisted.words.protocols.jabber import jid
from twisted.words.xish.domish import Element
from wokkel import pubsub

from collab import simulation as sim, portfolio as port
from collab.correlatedDefaultsSimulator import CorrelatedDefaultsSimulator
from collab.test import utils


testjid = jid.JID('test@master.local')

class CorrelatedDefaultsSimulatorTests(unittest.TestCase):
    """
    CorrelatedDefaultsSimulatorTests: Tests for the L{CorrelatedDefaultsSimulator} class
    
    """
    
    timeout = 2
    
    def setUp(self):
        self.cds = CorrelatedDefaultsSimulator(testjid)
        self.sch = utils.ClockScheduler(task.Clock())
        self.cds.coop = task.Cooperator(scheduler=self.sch.callLater)
    
    def tearDown(self):
    	pass
    
    def test_onGotItem_noParams(self):
        self.cds.onGotStartSimulation = Mock()
        self.cds.onGotStoppedSimulation = Mock()
        
        item = Element((pubsub.NS_PUBSUB_EVENT, 'item'))
        item['id'] = str(1)
        item.addElement('stuff', content='stuff that isnt parameters')

        d = self.cds.onGotItem(item)
        def check(data):
            self.assertTrue(data is None)
            self.assertFalse(self.cds.onGotStartSimulation.called)
            self.assertFalse(self.cds.onGotStoppedSimulation.called)

        d.addCallback(check)
        return d
    
    def test_onGotItem_start_alreadyGoing(self):
        self.cds.onGotStartSimulation = Mock()
        self.cds.onGotStoppedSimulation = Mock()
        run_id = '1'
        self.cds.tasks[run_id] = 'I should be a task'
        
        item = Element((pubsub.NS_PUBSUB_EVENT, 'item'))
        item['id'] = str(run_id)
        params = sim.Parameters(run_id=run_id, cmd='start')
        item.addChild(params.toElement())

        d = self.cds.onGotItem(item)
        def check(data):
            self.assertTrue(data is None)
            self.assertFalse(self.cds.onGotStartSimulation.called)
            self.assertFalse(self.cds.onGotStoppedSimulation.called)

        d.addCallback(check)
        return d
    
    def test_onGotItem_start_notAlreadyGoing(self):
        self.cds.onGotStartSimulation = Mock(side_effect=utils.good_side_effect('done'))
        self.cds.onGotStoppedSimulation = Mock()
        run_id = '1'
        
        item = Element((pubsub.NS_PUBSUB_EVENT, 'item'))
        item['id'] = str(run_id)
        params = sim.Parameters(run_id=run_id, cmd='start')
        item.addChild(params.toElement())

        self.assertFalse(run_id in self.cds.tasks)
        d = self.cds.onGotItem(item)
        def check(data):
            self.assertTrue(data is None)
            self.assertEquals(self.cds.onGotStartSimulation.call_count, 1)
            self.assertIn(run_id, self.cds.tasks)
            self.assertTrue(isinstance(self.cds.tasks[run_id], task.CooperativeTask))
            self.assertFalse(self.cds.onGotStoppedSimulation.called)

        d.addCallback(check)
        self.sch.clock.pump([1])
        return d
    
    def test_onGotItem_stop(self):
        self.cds.onGotStartSimulation = Mock()
        self.cds.onGotStoppedSimulation = Mock(side_effect=utils.good_side_effect('done'))
        run_id = '1'
        
        item = Element((pubsub.NS_PUBSUB_EVENT, 'item'))
        item['id'] = str(run_id)
        params = sim.Parameters(run_id=run_id, cmd='stop')
        item.addChild(params.toElement())

        d = self.cds.onGotItem(item)
        def check(data):
            self.assertEquals(data, 'done')
            self.assertEquals(self.cds.onGotStoppedSimulation.call_count, 1)
            self.assertFalse(self.cds.onGotStartSimulation.called)

        d.addCallback(check)
        self.sch.clock.pump([1])
        return d
    
    def test_onGotItem_info(self):
        self.cds.onGotStartSimulation = Mock()
        self.cds.onGotStoppedSimulation = Mock()
        run_id = '1'
        
        item = Element((pubsub.NS_PUBSUB_EVENT, 'item'))
        item['id'] = str(run_id)
        params = sim.Parameters(run_id=run_id, cmd='info')
        item.addChild(params.toElement())

        d = self.cds.onGotItem(item)
        def check(data):
            self.assertTrue(data is None)
            self.assertFalse(self.cds.onGotStartSimulation.called)
            self.assertFalse(self.cds.onGotStoppedSimulation.called)

        d.addCallback(check)
        self.sch.clock.pump([1])
        return d
    
    def test_onGotStartSimulation_noPortfolio(self):
        run_id = '1'
        item = Element((pubsub.NS_PUBSUB_EVENT, 'item'))
        item['id'] = str(run_id)
        params = sim.Parameters(run_id=run_id, cmd='info')
        params_el = item.addChild(params.toElement())
        logger = sim.Logger()

        self.cds.broadcastLogs = Mock(side_effect=utils.good_side_effect('done'))
        self.cds.broadcastResults = Mock()
        self.cds.simulatorFactory = MagicMock()
        self.cds._errback = Mock()

        gen = self.cds.onGotStartSimulation(params, item, logger)
        d = gen.next()

        def check(data):
            self.cds.broadcastLogs.assert_called_once_with(logger, params)
            self.assertFalse(self.cds.broadcastResults.called)
            self.assertFalse(self.cds.simulatorFactory.__getitem__.called)
            self.assertFalse(self.cds._errback.called)

        d.addCallback(check)
        self.assertRaises(StopIteration, gen.next)
        return d

    def test_onGotStartSimulation_withPortfolio_noBroadcast(self):
        run_id = '1'
        item = Element((pubsub.NS_PUBSUB_EVENT, 'item'))
        item['id'] = str(run_id)
        params = sim.Parameters(run_id=run_id, cmd='info')
        params_el = item.addChild(params.toElement())
        portfolio = port.Portfolio('jim')
        params_el.addChild(portfolio.toElement())
        logger = sim.Logger()

        self.cds.broadcastLogs = Mock()
        self.cds.broadcastResults = Mock()
        self.cds.simulatorFactory['sparse'] = MagicMock()
        self.cds._errback = Mock()
        
        simulator = Mock()
        simulator.copula = Mock()
        def simCreater(*a, **kw):
            return simulator
        self.cds.simulatorFactory['sparse'].side_effect = simCreater

        self.cds.max_runs = 6
        self.cds.broadcast_freq = 10
        chunk = 2
        t = task.Cooperator(scheduler=self.sch.callLater)
        
        d = t.coiterate(self.cds.onGotStartSimulation(params, item, logger, chunk))

        def check(data):
            self.assertFalse(self.cds.broadcastLogs.called)
            self.assertFalse(self.cds.broadcastResults.called)
            self.assertEquals(simulator.copula.call_count, 3)
            self.assertFalse(self.cds._errback.called)

        d.addCallback(check)
        self.sch.clock.pump([1,1,1])
        return d

    def test_onGotStartSimulation_withPortfolio_noBroadcast_noFactory(self):
        run_id = '1'
        item = Element((pubsub.NS_PUBSUB_EVENT, 'item'))
        item['id'] = str(run_id)
        params = sim.Parameters(run_id=run_id, cmd='info')
        params_el = item.addChild(params.toElement())
        portfolio = port.Portfolio('jim')
        params_el.addChild(portfolio.toElement())
        logger = sim.Logger()

        self.cds.broadcastLogs = Mock()
        self.cds.broadcastResults = Mock()
        self.cds.simulatorFactory = {}
        self.cds.simulatorFactory['sparse2'] = MagicMock()
        self.cds._errback = Mock()
        
        simulator = Mock()
        simulator.copula = Mock()
        def simCreater(*a, **kw):
            return simulator
        self.cds.simulatorFactory['sparse2'].side_effect = simCreater

        self.cds.max_runs = 6
        self.cds.broadcast_freq = 10
        chunk = 2
        t = task.Cooperator(scheduler=self.sch.callLater)
        
        d = t.coiterate(self.cds.onGotStartSimulation(params, item, logger, chunk))

        def check(data):
            self.assertFalse(self.cds.broadcastLogs.called)
            self.assertFalse(self.cds.broadcastResults.called)
            self.assertFalse(simulator.copula.called)
            self.assertTrue(self.cds._errback.called)

        d.addCallback(check)
        self.sch.clock.pump([1,1,1])
        return d

    def test_onGotStartSimulation_withPortfolio_twoBroadcast(self):
        run_id = '1'
        item = Element((pubsub.NS_PUBSUB_EVENT, 'item'))
        item['id'] = str(run_id)
        params = sim.Parameters(run_id=run_id, cmd='info')
        params_el = item.addChild(params.toElement())
        portfolio = port.Portfolio('jim')
        params_el.addChild(portfolio.toElement())
        logger = sim.Logger()

        self.cds.broadcastLogs = Mock()
        self.cds.broadcastResults = Mock(side_effect=utils.good_side_effect('results'))
        self.cds.simulatorFactory['sparse'] = MagicMock()
        self.cds._errback = Mock()
        
        simulator = Mock()
        simulator.copula = Mock()
        def simCreater(*a, **kw):
            return simulator
        self.cds.simulatorFactory['sparse'].side_effect = simCreater

        self.cds.max_runs = 15
        self.cds.broadcast_freq = 6
        chunk = 3
        t = task.Cooperator(scheduler=self.sch.callLater)
        
        d = t.coiterate(self.cds.onGotStartSimulation(params, item, logger, chunk))

        def check(data):
            self.assertFalse(self.cds.broadcastLogs.called)
            self.assertEquals(self.cds.broadcastResults.call_count, 2)
            self.assertEquals(simulator.copula.call_count, 5)
            self.assertFalse(self.cds._errback.called)

        d.addCallback(check)
        self.sch.clock.pump([1,1,1,1])
        return d

    def test_onGotStartSimulation_withPortfolio_twoBroadcastWithErrors(self):
        run_id = '1'
        item = Element((pubsub.NS_PUBSUB_EVENT, 'item'))
        item['id'] = str(run_id)
        params = sim.Parameters(run_id=run_id, cmd='info')
        params_el = item.addChild(params.toElement())
        portfolio = port.Portfolio('jim')
        params_el.addChild(portfolio.toElement())
        logger = sim.Logger()

        self.cds.broadcastLogs = Mock()
        self.cds.broadcastResults = Mock(side_effect=utils.good_side_effect('results'))
        self.cds.simulatorFactory['sparse'] = MagicMock()
        self.cds._errback = Mock()
        
        simulator = Mock()
        simulator.copula = Mock(side_effect=ValueError('%s: roar' % self.__class__))
        def simCreater(*a, **kw):
            return simulator
        self.cds.simulatorFactory['sparse'].side_effect = simCreater

        self.cds.max_runs = 15
        self.cds.broadcast_freq = 6
        chunk = 3
        t = task.Cooperator(scheduler=self.sch.callLater)
        
        d = t.coiterate(self.cds.onGotStartSimulation(params, item, logger, chunk))

        def check(data):
            self.assertFalse(self.cds.broadcastLogs.called)
            self.assertEquals(self.cds.broadcastResults.call_count, 2)
            self.assertEquals(simulator.copula.call_count, 5)
            self.assertTrue(self.cds._errback.called)

        d.addCallback(check)
        self.sch.clock.pump([1,1,1,1])
        return d

    def test_onGotStoppedSimulation_taskDone(self):
        run_id = '1'
        mockTask = Mock()
        mockTask.stop = Mock(side_effect=task.TaskDone)
        self.cds.tasks[run_id] = mockTask
        self.cds.broadcastStop = Mock(side_effect=utils.good_side_effect('Im pulling the wig down from the shelf'))
        params = sim.Parameters(run_id)

        d = self.cds.onGotStoppedSimulation(params)
        def check(data):
            self.assertEquals(data, 'Im pulling the wig down from the shelf')
            self.assertEquals(mockTask.stop.call_count, 1)
            self.assertFalse(run_id in self.cds.tasks)
            self.cds.broadcastStop.assert_called_once_with(params)

        d.addCallback(check)
        return d

    def test_onGotStoppedSimulation_taskStopped(self):
        run_id = '1'
        mockTask = Mock()
        mockTask.stop = Mock(side_effect=task.TaskStopped)
        self.cds.tasks[run_id] = mockTask
        self.cds.broadcastStop = Mock(side_effect=utils.good_side_effect('Suddenly Im Miss Farrah Fawcett'))
        params = sim.Parameters(run_id)

        d = self.cds.onGotStoppedSimulation(params)
        def check(data):
            self.assertEquals(data, 'Suddenly Im Miss Farrah Fawcett')
            self.assertEquals(mockTask.stop.call_count, 1)
            self.assertFalse(run_id in self.cds.tasks)
            self.cds.broadcastStop.assert_called_once_with(params)

        d.addCallback(check)
        return d

    def test_onGotStoppedSimulation_taskFailed(self):
        run_id = '1'
        mockTask = Mock()
        mockTask.stop = Mock(side_effect=task.TaskFailed)
        self.cds.tasks[run_id] = mockTask
        self.cds.broadcastStop = Mock(side_effect=utils.good_side_effect('from TV'))
        params = sim.Parameters(run_id)

        d = self.cds.onGotStoppedSimulation(params)
        def check(data):
            self.assertEquals(data, 'from TV')
            self.assertEquals(mockTask.stop.call_count, 1)
            self.assertFalse(run_id in self.cds.tasks)
            self.cds.broadcastStop.assert_called_once_with(params)

        d.addCallback(check)
        return d

    def test_onGotStoppedSimulation_taskFinished(self):
        run_id = '1'
        mockTask = Mock()
        mockTask.stop = Mock(side_effect=task.TaskFinished)
        self.cds.tasks[run_id] = mockTask
        self.cds.broadcastStop = Mock(side_effect=utils.good_side_effect('until I wake up'))
        params = sim.Parameters(run_id)

        d = self.cds.onGotStoppedSimulation(params)
        def check(data):
            self.assertEquals(data, 'until I wake up')
            self.assertEquals(mockTask.stop.call_count, 1)
            self.assertFalse(run_id in self.cds.tasks)
            self.cds.broadcastStop.assert_called_once_with(params)

        d.addCallback(check)
        return d

    def test_onGotStoppedSimulation(self):
        run_id = '1'
        mockTask = Mock()
        mockTask.stop = Mock()
        self.cds.tasks[run_id] = mockTask
        self.cds.broadcastStop = Mock(side_effect=utils.good_side_effect('everything went better than expected'))
        params = sim.Parameters(run_id)

        d = self.cds.onGotStoppedSimulation(params)
        def check(data):
            self.assertEquals(data, 'everything went better than expected')
            self.assertEquals(mockTask.stop.call_count, 1)
            self.assertFalse(run_id in self.cds.tasks)
            self.cds.broadcastStop.assert_called_once_with(params)

        d.addCallback(check)
        return d

    def test_onGotStoppedSimulation_noRunId(self):
        run_id = '2'
        mockTask = Mock()
        mockTask.stop = Mock()
        self.cds.tasks[run_id] = mockTask
        self.cds.broadcastStop = Mock(side_effect=utils.good_side_effect('everything went better than expected'))
        params = sim.Parameters('1')

        d = self.cds.onGotStoppedSimulation(params)
        def check(data):
            self.assertTrue(data is None)
            self.assertFalse(mockTask.stop.called)
            self.assertTrue(run_id in self.cds.tasks)
            self.assertFalse(self.cds.broadcastStop.called)

        d.addCallback(check)
        return d

    def test_broadcastresults(self):
        params = sim.Parameters(1, cmd='stop')
        progress = sim.Progress(200)
        dists = sim.Distributions()
        self.cds.outputNode.onOutput = Mock(side_effect=utils.good_side_effect('and turn back to myself'))
        
        d = self.cds.broadcastResults(params, progress, dists)
        def check(data):
            self.assertEquals(self.cds.outputNode.onOutput.call_count, 1)
            args = self.cds.outputNode.onOutput.call_args_list
            expected = sim.Parameters(1, cmd='results', timestamp=params.timestamp).toElement()
            expected.addChild(dists.toElement())
            expected.addChild(progress.toElement())
            self.assertEquals(args[0][1]['data'].toXml(), expected.toXml())

        d.addCallback(check)
        return d
                              
        
