# Copyright (c) Simon Parry.
# See LICENSE for details.

from mock import Mock
from twisted.internet import defer
from twisted.trial import unittest
from twisted.words.protocols.jabber import jid
from twisted.words.xish.domish import Element
from wokkel import pubsub

from collab import portfolio, simulation
from collab.correlatedDefaultsManager import CorrelatedDefaultsManager
from collab.test import utils


testjid = jid.JID('test@master.local')
    
class CorrelatedDefaultsManagerTests(unittest.TestCase):
    """
    CorrelatedDefaultsManagerTests: Tests for the L{CorrelatedDefaultsManager} class
    
    """
    
    timeout = 2
    
    def setUp(self):
        pass
    
    def tearDown(self):
    	pass
        
    @defer.inlineCallbacks
    def test_broadcastStart(self):
        cdm = CorrelatedDefaultsManager(testjid)
        cdm.outputNode.onOutput = Mock(side_effect=utils.good_side_effect('lush'))

        params = simulation.Parameters()
        port = portfolio.Portfolio('p1')
        out = yield cdm.broadcastStart(params, port)

        self.assertEquals(cdm.outputNode.onOutput.call_count, 1)
        
        expected = simulation.Parameters(cmd='start', timestamp=params.timestamp).toElement()
        expected.addChild(portfolio.Portfolio('p1').toElement())
        
        for (a, dic) in cdm.outputNode.onOutput.call_args_list:
            self.assertEquals(expected.toXml(), dic['data'].toXml())

    @defer.inlineCallbacks
    def test_onGotItem_noParams(self):
        cdm = CorrelatedDefaultsManager(testjid)
        cdm.broadcastStart = Mock()
        cdm.broadcastStop = Mock()
        cdm.broadcastLogs = Mock()
        
        item = Element((pubsub.NS_PUBSUB_EVENT, 'item'))
        item['id'] = str(1)
        item.addElement('stuff', content='stuff that isnt parameters')

        out = yield cdm.onGotItem(item)

        self.assertFalse(cdm.broadcastStart.called)
        self.assertFalse(cdm.broadcastStop.called)
        self.assertFalse(cdm.broadcastLogs.called)

    @defer.inlineCallbacks
    def test_onGotItem_stopping(self):
        cdm = CorrelatedDefaultsManager(testjid)
        cdm.broadcastStart = Mock()
        cdm.broadcastStop = Mock(side_effect=utils.good_side_effect('lush'))
        cdm.broadcastLogs = Mock()
        
        item = Element((pubsub.NS_PUBSUB_EVENT, 'item'))
        item['id'] = str(1)
        params = simulation.Parameters(cmd='stop')
        expected = params.toElement()
        item.addChild(expected)

        out = yield cdm.onGotItem(item)

        self.assertFalse(cdm.broadcastStart.called)
        self.assertEquals(cdm.broadcastStop.call_count, 1)
        self.assertFalse(cdm.broadcastLogs.called)

        for ((a,), dic) in cdm.broadcastStop.call_args_list:
            self.assertEquals(a.toElement().toXml(), expected.toXml())

    @defer.inlineCallbacks
    def test_onGotItem_startNoRunId(self):
        cdm = CorrelatedDefaultsManager(testjid)
        cdm.broadcastStart = Mock()
        cdm.broadcastStop = Mock()
        cdm.broadcastLogs = Mock(side_effect=utils.good_side_effect('lush'))
        
        item = Element((pubsub.NS_PUBSUB_EVENT, 'item'))
        params = simulation.Parameters(cmd='start')
        p = item.addChild(params.toElement())
        p.addChild(portfolio.Portfolio('p1').toElement())
        expected = simulation.Parameters(cmd='start', run_id=None, timestamp=params.timestamp).toElement()

        out = yield cdm.onGotItem(item)

        self.assertFalse(cdm.broadcastStart.called)
        self.assertEquals(cdm.broadcastLogs.call_count, 1)
        self.assertFalse(cdm.broadcastStop.called)

        for ((a,b), dic) in cdm.broadcastLogs.call_args_list:
            self.assertEquals(b.toElement().toXml(), expected.toXml())

    @defer.inlineCallbacks
    def test_onGotItem_startNoPortfolio(self):
        cdm = CorrelatedDefaultsManager(testjid)
        cdm.broadcastStart = Mock()
        cdm.broadcastStop = Mock()
        cdm.broadcastLogs = Mock(side_effect=utils.good_side_effect('lush'))
        
        item = Element((pubsub.NS_PUBSUB_EVENT, 'item'))
        item['id'] = str(1)
        params = simulation.Parameters(cmd='start')
        item.addChild(params.toElement())
        expected = simulation.Parameters(cmd='start', run_id='1', timestamp=params.timestamp).toElement()
        
        out = yield cdm.onGotItem(item)

        self.assertFalse(cdm.broadcastStart.called)
        self.assertEquals(cdm.broadcastLogs.call_count, 1)
        self.assertFalse(cdm.broadcastStop.called)

        for ((a,b), dic) in cdm.broadcastLogs.call_args_list:
            self.assertEquals(b.toElement().toXml(), expected.toXml())

    @defer.inlineCallbacks
    def test_onGotItem_start(self):
        cdm = CorrelatedDefaultsManager(testjid)
        cdm.broadcastStart = Mock(side_effect=utils.good_side_effect('lush'))
        cdm.broadcastStop = Mock()
        cdm.broadcastLogs = Mock()
        
        item = Element((pubsub.NS_PUBSUB_EVENT, 'item'))
        item['id'] = str(1)
        params = simulation.Parameters(cmd='start')
        p = item.addChild(params.toElement())
        p.addChild(portfolio.Portfolio('p1').toElement())

        expectedParams = simulation.Parameters(cmd='start', run_id='1', timestamp=params.timestamp).toElement()
        expectedPort = portfolio.Portfolio('p1').toElement()

        out = yield cdm.onGotItem(item)

        self.assertEquals(cdm.broadcastStart.call_count, 1)
        self.assertFalse(cdm.broadcastLogs.called)
        self.assertFalse(cdm.broadcastStop.called)

        for ((a,b), dic) in cdm.broadcastStart.call_args_list:
            self.assertEquals(a.toElement().toXml(), expectedParams.toXml())
            self.assertEquals(b.toElement().toXml(), expectedPort.toXml())
        
