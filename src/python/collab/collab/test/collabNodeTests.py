# Copyright (c) Simon Parry.
# See LICENSE for details.

from mock import Mock
from twisted.internet import task
from twisted.test.test_task import TestableLoopingCall
from twisted.trial import unittest
from twisted.words.protocols.jabber import jid
from twisted.words.xish.domish import Element
from wokkel import pubsub

import collab
from collab import simulation as sim
from collab.collabNode import CollabNode
from collab.test import utils


testjid = jid.JID('test@master.local')

class CollabNodeTests(unittest.TestCase):
    """
    CollabNodeTests: Tests for the L{collabNode} class
    
    """
    
    timeout = 2
    
    def setUp(self):
        self.clab = CollabNode(testjid)
        self.sch = utils.ClockScheduler(task.Clock())
        self.clab.coop = task.Cooperator(scheduler=self.sch.callLater)

    def tearDown(self):
    	pass
    
    def _makeItem(self, n, cmd):
        item = Element((pubsub.NS_PUBSUB_EVENT, 'item'))
        item['id'] = str(n)
        params = sim.Parameters(run_id=str(n), cmd=cmd)
        params_el = params.toElement()
        params_el.addChild(sim.Progress(200).toElement())
        params_el.addChild(sim.Distributions().toElement())
        item.addChild(params_el)
        return item

    def _makeItems(self, m, cmd='results'):
        items = [self._makeItem(i, cmd) for i in xrange(m)]
        sender = jid.JID('sender@master.local')
        node = u'dist_manager'
        headers = {}
        return pubsub.ItemsEvent(sender, testjid, node, items, headers)

    def test_itemsReceived(self):
        self.clab.onGotItem = Mock(side_effect=utils.good_side_effect('lush'))
        self.clab._errback = Mock()
        ev = self._makeItems(3)
        d = self.clab.itemsReceived(ev)
        
        def check(data):
            self.assertEquals(self.clab.onGotItem.call_count, 3)
            expected = [((i,), {}) for i in ev.items]
            self.assertEquals(self.clab.onGotItem.call_args_list, expected)
            self.assertFalse(self.clab._errback.called)

        d.addCallback(check)
        self.sch.clock.pump([1,2,3])
        return d

    def test_itemsReceived_bad(self):
        self.clab.onGotItem = Mock(side_effect=utils.bad_side_effect(Exception('%s: not lush' % self.__class__)))
        self.clab._errback = Mock(side_effect=utils.good_side_effect('lush'))
        ev = self._makeItems(3)
        d = self.clab.itemsReceived(ev)
        
        def check(data):
            self.assertEquals(self.clab.onGotItem.call_count, 3)
            expected = [((i,), {}) for i in ev.items]
            self.assertEquals(self.clab.onGotItem.call_args_list, expected)
            self.assertTrue(self.clab._errback.call_count, 3)

        d.addCallback(check)
        self.sch.clock.pump([1,2,3])
        return d

    def test_connectionInitialized_startLoadbalancer(self):
        self.clab.xmlstream = Mock()
        self.clab.xmlstream.addObserver = Mock()
        self.clab.loopingLoadBalancer.running = False
        self.clab.loopingLoadBalancer.start = Mock(side_effect=utils.good_side_effect('lush'))
        self.clab._errback = Mock(side_effect=utils.good_side_effect('lush'))

        d = self.clab.connectionInitialized()

        def check(data):
            self.assertEquals(self.clab.xmlstream.addObserver.call_count, 2) #calls base class too
            self.clab.loopingLoadBalancer.start.assert_called_once_with(collab.DEFAULT_LOAD_BALANCER_FREQ)
            self.assertFalse(self.clab._errback.called)

        d.addCallback(check)
        return d

    def test_connectionInitialized_startLoadbalancer_bad(self):
        self.clab.xmlstream = Mock()
        self.clab.xmlstream.addObserver = Mock()
        self.clab.loopingLoadBalancer.running = False
        self.clab.loopingLoadBalancer.start = Mock(side_effect=utils.bad_side_effect(ValueError('%s: arrgh' % self.__class__)))
        self.clab._errback = Mock(side_effect=utils.good_side_effect('lush'))

        d = self.clab.connectionInitialized()

        def check(data):
            self.assertEquals(self.clab.xmlstream.addObserver.call_count, 2) #calls base class too
            self.clab.loopingLoadBalancer.start.assert_called_once_with(collab.DEFAULT_LOAD_BALANCER_FREQ)
            self.assertEquals(self.clab._errback.call_count, 1)

        d.addCallback(check)
        return d

    def test_connectionInitialized_startedLoadbalancer(self):
        self.clab.xmlstream = Mock()
        self.clab.xmlstream.addObserver = Mock()
        self.clab.loopingLoadBalancer.running = True
        self.clab.loopingLoadBalancer.start = Mock()
        self.clab._errback = Mock(side_effect=utils.good_side_effect('lush'))

        d = self.clab.connectionInitialized()

        def check(data):
            self.assertEquals(self.clab.xmlstream.addObserver.call_count, 2) #calls base class too
            self.assertFalse(self.clab.loopingLoadBalancer.start.called)
            self.assertFalse(self.clab._errback.called)

        d.addCallback(check)
        return d

    def test_connectionInitialized_loopingBalancerWorks(self):
        clock = task.Clock()
        mockCheckLoading = Mock(side_effect=utils.good_side_effect('lush'))
        lc = TestableLoopingCall(clock, mockCheckLoading)
        clab = CollabNode(testjid, loopingLoadBalancer=lc)
        self.assertIdentical(clab.loopingLoadBalancer, lc)

        # dont need these to happen
        clab.xmlstream = Mock()
        clab.xmlstream.addObserver = Mock()

        self.assertFalse(clab.loopingLoadBalancer.running)
        d = clab.connectionInitialized()
        self.assertTrue(clab.loopingLoadBalancer.running)

        repeats = 3
        def check(data):
            self.assertEquals(mockCheckLoading.call_count, repeats)
        d.addCallback(check)
        
        # pump it (repeats-1) times as it has already called once on looping startup
        timings = [collab.DEFAULT_LOAD_BALANCER_FREQ for i in xrange(repeats-1)]
        clock.pump(timings)

        lc.stop()

        self.failIf(clock.calls)

        return d

    def test_connectionInitialized_loopingBalancerWorksInClass(self):
        clock = task.Clock()
        self.clab._checkLoading = Mock(side_effect=utils.good_side_effect('lush'))
        self.clab.loopingLoadBalancer = TestableLoopingCall(clock, self.clab._checkLoading)

        # dont need these to happen
        self.clab.xmlstream = Mock()
        self.clab.xmlstream.addObserver = Mock()

        self.assertFalse(self.clab.loopingLoadBalancer.running)
        d = self.clab.connectionInitialized()
        self.assertTrue(self.clab.loopingLoadBalancer.running)

        repeats = 3
        def check(data):
            self.assertEquals(self.clab._checkLoading.call_count, repeats)
        d.addCallback(check)
        
        # pump it (repeats-1) times as it has already called once on looping startup
        timings = [collab.DEFAULT_LOAD_BALANCER_FREQ for i in xrange(repeats-1)]
        clock.pump(timings)

        self.clab.loopingLoadBalancer.stop()

        self.failIf(self.sch.clock.calls)

        return d

    def test_checkLoading_overloadedBalancerNotOverloaded(self):
        self.clab.overloaded = True
        self.clab.inputs = set(['1','2','3'])
        self.clab._errback = Mock(side_effect=utils.good_side_effect('lush'))

        loadbalancer = Mock()
        loadbalancer.overloaded = Mock(return_value=False)
        loadbalancer.reloadAll = Mock(side_effect=utils.good_side_effect('lush'))
        loadbalancer.suspendAll = Mock(side_effect=utils.good_side_effect('lush'))

        d = self.clab._checkLoading(loadbalancer)

        def check(data):
            self.assertEquals(loadbalancer.overloaded.call_count, 1)
            self.assertFalse(self.clab.overloaded)
            loadbalancer.reloadAll.assert_called_once_with(self.clab.inputNode, set(['1','2','3']))
            self.assertFalse(loadbalancer.suspendAll.called)
            self.assertEquals(self.clab.inputs, set())
            self.assertFalse(self.clab._errback.called)

        d.addCallback(check)
        return d

    def test_checkLoading_overloadedBalancerNotOverloaded_badReloadAll(self):
        self.clab.overloaded = True
        self.clab.inputs = set(['1','2','3'])
        self.clab._errback = Mock(side_effect=utils.good_side_effect('lush'))

        loadbalancer = Mock()
        loadbalancer.overloaded = Mock(return_value=False)
        loadbalancer.reloadAll = Mock(side_effect=utils.bad_side_effect(Exception('%s: aargh' % self.__class__)))
        loadbalancer.suspendAll = Mock(side_effect=utils.good_side_effect('lush'))

        d = self.clab._checkLoading(loadbalancer)

        def check(data):
            self.assertEquals(loadbalancer.overloaded.call_count, 1)
            self.assertTrue(self.clab.overloaded)
            loadbalancer.reloadAll.assert_called_once_with(self.clab.inputNode, set(['1','2','3']))
            self.assertFalse(loadbalancer.suspendAll.called)
            self.assertEquals(self.clab.inputs, set(['1','2','3']))
            self.assertTrue(self.clab._errback.called)

        d.addCallback(check)
        return d

    def test_checkLoading_overloadedBalancerOverloaded(self):
        self.clab.overloaded = True
        self.clab.inputs = set(['1','2','3'])
        self.clab._errback = Mock(side_effect=utils.good_side_effect('lush'))

        loadbalancer = Mock()
        loadbalancer.overloaded = Mock(return_value=True)
        loadbalancer.reloadAll = Mock(side_effect=utils.good_side_effect('lush'))
        loadbalancer.suspendAll = Mock(side_effect=utils.good_side_effect('lush'))

        d = self.clab._checkLoading(loadbalancer)

        def check(data):
            self.assertEquals(loadbalancer.overloaded.call_count, 1)
            self.assertTrue(self.clab.overloaded)
            self.assertFalse(loadbalancer.reloadAll.called)
            self.assertFalse(loadbalancer.suspendAll.called)
            self.assertEquals(self.clab.inputs, set(['1','2','3']))
            self.assertFalse(self.clab._errback.called)

        d.addCallback(check)
        return d

    def test_checkLoading_notOverloadedBalancerNotOverloaded(self):
        self.clab.overloaded = False
        self.clab.inputs = set(['1','2','3'])
        self.clab._errback = Mock(side_effect=utils.good_side_effect('lush'))

        loadbalancer = Mock()
        loadbalancer.overloaded = Mock(return_value=False)
        loadbalancer.reloadAll = Mock(side_effect=utils.good_side_effect('lush'))
        loadbalancer.suspendAll = Mock(side_effect=utils.good_side_effect('lush'))

        d = self.clab._checkLoading(loadbalancer)

        def check(data):
            self.assertEquals(loadbalancer.overloaded.call_count, 1)
            self.assertFalse(self.clab.overloaded)
            self.assertFalse(loadbalancer.reloadAll.called)
            self.assertFalse(loadbalancer.suspendAll.called)
            self.assertEquals(self.clab.inputs, set(['1','2','3']))
            self.assertFalse(self.clab._errback.called)

        d.addCallback(check)
        return d

    def test_checkLoading_notOverloadedBalancerOverloaded(self):
        self.clab.overloaded = False
        self.clab.inputs = set(['1','2','3'])
        self.clab._errback = Mock(side_effect=utils.good_side_effect('lush'))

        loadbalancer = Mock()
        loadbalancer.overloaded = Mock(return_value=True)
        loadbalancer.reloadAll = Mock(side_effect=utils.good_side_effect('lush'))
        loadbalancer.suspendAll = Mock(side_effect=utils.good_side_effect(set(['1'])))

        d = self.clab._checkLoading(loadbalancer)

        def check(data):
            self.assertEquals(loadbalancer.overloaded.call_count, 1)
            self.assertTrue(self.clab.overloaded)
            self.assertFalse(loadbalancer.reloadAll.called)
            loadbalancer.suspendAll.assert_called_once_with(self.clab.inputNode)
            self.assertEquals(self.clab.inputs, set(['1']))
            self.assertFalse(self.clab._errback.called)

        d.addCallback(check)
        return d

    def test_checkLoading_notOverloadedBalancerOverloaded_badSuspendAll(self):
        self.clab.overloaded = False
        self.clab.inputs = set(['1','2','3'])
        self.clab._errback = Mock(side_effect=utils.good_side_effect('lush'))

        loadbalancer = Mock()
        loadbalancer.overloaded = Mock(return_value=True)
        loadbalancer.reloadAll = Mock(side_effect=utils.good_side_effect('lush'))
        loadbalancer.suspendAll = Mock(side_effect=utils.bad_side_effect(Exception('%s: aargh' % self.__class__)))

        d = self.clab._checkLoading(loadbalancer)

        def check(data):
            self.assertEquals(loadbalancer.overloaded.call_count, 1)
            self.assertFalse(self.clab.overloaded)
            self.assertFalse(loadbalancer.reloadAll.called)
            loadbalancer.suspendAll.assert_called_once_with(self.clab.inputNode)
            self.assertEquals(self.clab.inputs, set(['1','2','3']))
            self.assertTrue(self.clab._errback.called)

        d.addCallback(check)
        return d

    def test_broadcastStop(self):
        self.clab.outputNode.onOutput = Mock(side_effect=utils.good_side_effect('lush'))

        params = sim.Parameters(run_id='1', output='out', number_runs=1000, cmd='start')

        expected = sim.Parameters(run_id='1', output='out', number_runs=1000, cmd='stop', timestamp=params.timestamp).toElement()
        
        d = self.clab.broadcastStop(params)
        def check(data):
            self.assertEquals(self.clab.outputNode.onOutput.call_count, 1)
            args = self.clab.outputNode.onOutput.call_args_list
            self.assertEquals(len(args), 1)
            self.assertEquals(args[0][1]['data'].toXml(), expected.toXml())
            

        d.addCallback(check)
        return d

    def test_broadcastLogs(self):
        self.clab.errorNode.onError = Mock(side_effect=utils.good_side_effect('lush'))

        params = sim.Parameters(run_id='1', output='out', number_runs=1000, cmd='start')
        logger = sim.Logger()

        expected = sim.Parameters(run_id='1', output='out', number_runs=1000, cmd='info', timestamp=params.timestamp).toElement()
        expected.addChild(sim.Logger().toElement())
        
        d = self.clab.broadcastLogs(logger, params)
        def check(data):
            self.assertEquals(data, 'lush')
            self.assertEquals(self.clab.errorNode.onError.call_count, 1)
            args = self.clab.errorNode.onError.call_args_list
            self.assertEquals(len(args), 1)
            self.assertEquals(args[0][1]['error'].toXml(), expected.toXml())
            

        d.addCallback(check)
        return d

    def test_errback_okBroadcast(self):
        self.clab.broadcastLogs = Mock(side_effect=utils.good_side_effect('lush'))
        err = ValueError('roar')
        logs = sim.Logger()
        logs.addLog = Mock()
        params = sim.Parameters()

        d = self.clab._errback(err, logs, params)
        def check(data):
            logs.addLog.assert_called_once_with(collab.ERROR_EL, str(err))
            self.clab.broadcastLogs.assert_called_once_with(logs, params)

        d.addCallback(check)
        return d

    def test_errback_badBroadcast(self):
        self.clab.broadcastLogs = Mock(side_effect=utils.bad_side_effect(Exception('%s: roarrr' % self.__class__)))
        err = ValueError('roar')
        logs = sim.Logger()
        logs.addLog = Mock()
        params = sim.Parameters()

        d = self.clab._errback(err, logs, params)
        def check(data):
            logs.addLog.assert_called_once_with(collab.ERROR_EL, str(err))
            self.clab.broadcastLogs.assert_called_once_with(logs, params)

        d.addCallback(check)
        return d
