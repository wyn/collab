# Copyright (c) Simon Parry.
# See LICENSE for details.

#tests for nodes module
from mock import Mock, patch
from twisted.internet import defer, task
from twisted.trial import unittest
from twisted.words.protocols.jabber import jid, error
from twisted.words.xish.domish import Element
from wokkel import pubsub as ps

from collab import nodes
from collab.test import utils


testJid = jid.JID('test@master.local')

class PSInputNodeTests(unittest.TestCase):

    timeout = 2

    def setUp(self):
        self.mockPSClient = Mock()
        self.mockPSClient.subscribe = Mock(side_effect=utils.good_side_effect('cool'))
        self.mockPSClient.unsubscribe = Mock(side_effect=utils.good_side_effect('cool'))

        self.subs = set([
            ps.Subscription(
                nodeIdentifier='node1',
                subscriber='test1@master.local',
                state='subscribed',
                subscriptionIdentifier=1
                ),
            ps.Subscription(
                nodeIdentifier='node2',
                subscriber='test1@master.local',
                state='subscribed',
                subscriptionIdentifier=2
                )
            ])
                       
        
    def tearDown(self):
        pass

    @patch('collab.pubsubRequestWithAffiliations.getSubscriptionsForJid')
    def test_inputChannels(self, getSubsMock):
        getSubsMock.side_effect = utils.good_side_effect(self.subs)
        xsMock = Mock()
        self.mockPSClient.xmlstream = xsMock
        node = nodes.PSInputNode(testJid, self.mockPSClient)

        d = node.inputChannels()
        def cb(subs):
            getSubsMock.assert_called_once_with(testJid, xsMock)
            self.assertEquals(len(subs), 2)
            for n in ['node1', 'node2']:
                self.assertIn(n, subs)

        d.addCallback(cb)
        return d

    @patch('collab.pubsubRequestWithAffiliations.getSubscriptionsForJid')
    def test_inputChannels_none(self, getSubsMock):
        getSubsMock.side_effect = utils.good_side_effect([])
        xsMock = Mock()
        self.mockPSClient.xmlstream = xsMock
        node = nodes.PSInputNode(testJid, self.mockPSClient)

        d = node.inputChannels()
        def cb(subs):
            getSubsMock.assert_called_once_with(testJid, xsMock)
            self.assertEquals([], subs)

        d.addCallback(cb)
        return d
            
    
    @defer.inlineCallbacks
    def test_addInput_new(self):
        testNodes = ['1', '2', '3']
        node = nodes.PSInputNode(testJid, self.mockPSClient)
        node.inputChannels = Mock(side_effect=utils.good_side_effect(testNodes))

        yield node.addInput('4')

        self.assertTrue(self.mockPSClient.subscribe.called)
        
    @defer.inlineCallbacks
    def test_addInput_alreadyThere(self):
        testNodes = ['1', '2', '3']
        node = nodes.PSInputNode(testJid, self.mockPSClient)
        node.inputChannels = Mock(side_effect=utils.good_side_effect(testNodes))

        yield node.addInput('2')

        self.assertFalse(self.mockPSClient.subscribe.called)

    @defer.inlineCallbacks
    def test_removeInput_notThere(self):
        testNodes = ['1', '2', '3']
        node = nodes.PSInputNode(testJid, self.mockPSClient)
        node.inputChannels = Mock(side_effect=utils.good_side_effect(testNodes))

        yield node.removeInput('4')

        self.assertFalse(self.mockPSClient.unsubscribe.called)
        
    @defer.inlineCallbacks
    def test_removeInput_alreadyThere(self):
        testNodes = ['1', '2', '3']
        node = nodes.PSInputNode(testJid, self.mockPSClient)
        node.inputChannels = Mock(side_effect=utils.good_side_effect(testNodes))

        yield node.removeInput('2')

        self.assertTrue(self.mockPSClient.unsubscribe.called)



class PSOutputNodeTests(unittest.TestCase):

    timeout = 2

    def setUp(self):
        self.mockPSClient = Mock()
        self.mockPSClient.publish = Mock(side_effect=utils.good_side_effect('lush'))
        
    def tearDown(self):
        pass

    @patch('collab.pubsubRequestWithAffiliations.getAffiliationsForJid')
    def test_outputChannels(self, getAffsMock):
        testaffs = {
            'node1': 'publisher',
            'node2': 'publisher',
            }
        getAffsMock.side_effect = utils.good_side_effect(testaffs)
        xsMock = Mock()
        self.mockPSClient.xmlstream = xsMock
        node = nodes.PSOutputNode(testJid, self.mockPSClient)

        d = node.outputChannels()
        def cb(affs):
            getAffsMock.assert_called_once_with(testJid, xsMock)
            self.assertEquals(['log', 'node1', 'node2'], affs)

        d.addCallback(cb)
        return d

    @patch('collab.pubsubRequestWithAffiliations.getAffiliationsForJid')
    def test_outputChannels_noPublishers(self, getAffsMock):
        testaffs = {
            'node1': 'owner',
            'node2': 'subscriber',
            }
        getAffsMock.side_effect = utils.good_side_effect(testaffs)
        xsMock = Mock()
        self.mockPSClient.xmlstream = xsMock
        node = nodes.PSOutputNode(testJid, self.mockPSClient)

        d = node.outputChannels()
        def cb(affs):
            getAffsMock.assert_called_once_with(testJid, xsMock)
            self.assertEquals(['log'], affs)

        d.addCallback(cb)
        return d

    @patch('collab.pubsubRequestWithAffiliations.getAffiliationsForJid')
    def test_outputChannels_errorNodes(self, getAffsMock):
        testaffs = {
            'errornode1': 'publisher',
            'errornode2': 'publisher',
            }
        getAffsMock.side_effect = utils.good_side_effect(testaffs)
        xsMock = Mock()
        self.mockPSClient.xmlstream = xsMock
        node = nodes.PSOutputNode(testJid, self.mockPSClient)

        d = node.outputChannels()
        def cb(affs):
            getAffsMock.assert_called_once_with(testJid, xsMock)
            self.assertEquals(['log'], affs)

        d.addCallback(cb)
        return d

    def test_onOutput_toLog(self):
        outputs = ['log']
        node = nodes.PSOutputNode(testJid, self.mockPSClient)
        node.outputChannels = Mock(side_effect=utils.good_side_effect(outputs))
        
        el = Element(('top', 'ns'))
        el.addContent('im covered in bees')
        el.toXml = Mock()
        d = node.onOutput(el)

        def cb(msg):
            self.assertFalse(self.mockPSClient.publish.called)
            self.assertEquals(el.toXml.call_count, 1)

        d.addCallback(cb)
        return d

    def test_onOutput_toPublishOnly(self):
        outputs = ['node1', 'node2']
        node = nodes.PSOutputNode(testJid, self.mockPSClient)
        node.outputChannels = Mock(side_effect=utils.good_side_effect(outputs))
        
        el = Element(('top', 'ns'))
        el.addContent('im covered in bees')
        el.toXml = Mock()
        d = node.onOutput(el)

        def cb(msg):
            self.assertEquals(self.mockPSClient.publish.call_count, 2)
            self.assertEquals(el.toXml.call_count, 0)

        d.addCallback(cb)
        return d 

    def test_onOutput_toPublishErrored(self):
        self.mockPSClient.publish = Mock(side_effect=utils.bad_side_effect(error.StanzaError('DISAPPOINTED')))
        outputs = ['node1', 'node2', 'log']
        node = nodes.PSOutputNode(testJid, self.mockPSClient)
        node.outputChannels = Mock(side_effect=utils.good_side_effect(outputs))
        
        el = Element(('top', 'ns'))
        el.addContent('im covered in bees')
        el.toXml = Mock()
        d = node.onOutput(el)

        def cb(msg):
            self.assertEquals(self.mockPSClient.publish.call_count, 2)
            self.assertEquals(el.toXml.call_count, 1)

        d.addCallback(cb)
        return self.assertFailure(d, error.StanzaError)
   
class PSErrorNodeTests(unittest.TestCase):

    timeout = 2

    def setUp(self):
        self.mockPSClient = Mock()
        self.mockPSClient.publish = Mock(side_effect=utils.good_side_effect('lush'))
        
    def tearDown(self):
        pass

    @patch('collab.pubsubRequestWithAffiliations.getAffiliationsForJid')
    def test_errorChannels(self, getAffsMock):
        testaffs = {
            'errornode1': 'publisher',
            'errornode2': 'publisher',
            }
        getAffsMock.side_effect = utils.good_side_effect(testaffs)
        xsMock = Mock()
        self.mockPSClient.xmlstream = xsMock
        node = nodes.PSErrorNode(testJid, self.mockPSClient)

        d = node.errorChannels()
        def cb(affs):
            getAffsMock.assert_called_once_with(testJid, xsMock)
            self.assertEquals(['log', 'errornode1', 'errornode2'], affs)

        d.addCallback(cb)
        return d

    @patch('collab.pubsubRequestWithAffiliations.getAffiliationsForJid')
    def test_errorChannels_noPublishers(self, getAffsMock):
        testaffs = {
            'node1': 'owner',
            'node2': 'subscriber',
            }
        getAffsMock.side_effect = utils.good_side_effect(testaffs)
        xsMock = Mock()
        self.mockPSClient.xmlstream = xsMock
        node = nodes.PSErrorNode(testJid, self.mockPSClient)

        d = node.errorChannels()
        def cb(affs):
            getAffsMock.assert_called_once_with(testJid, xsMock)
            self.assertEquals(['log'], affs)

        d.addCallback(cb)
        return d

    @patch('collab.pubsubRequestWithAffiliations.getAffiliationsForJid')
    def test_errorChannels_notErrorNodes(self, getAffsMock):
        testaffs = {
            'node1': 'publisher',
            'node2': 'publisher',
            }
        getAffsMock.side_effect = utils.good_side_effect(testaffs)
        xsMock = Mock()
        self.mockPSClient.xmlstream = xsMock
        node = nodes.PSErrorNode(testJid, self.mockPSClient)

        d = node.errorChannels()
        def cb(affs):
            getAffsMock.assert_called_once_with(testJid, xsMock)
            self.assertEquals(['log'], affs)

        d.addCallback(cb)
        return d

    def test_onError_toLog(self):
        errors = ['log']
        node = nodes.PSErrorNode(testJid, self.mockPSClient)
        node.errorChannels = Mock(side_effect=utils.good_side_effect(errors))
        
        el = Element(('top', 'ns'))
        el.addContent('im covered in bees')
        el.toXml = Mock()
        d = node.onError(el)

        def cb(msg):
            self.assertFalse(self.mockPSClient.publish.called)
            self.assertEquals(el.toXml.call_count, 1)

        d.addCallback(cb)
        return d

    def test_onError_toPublishOnly(self):
        errors = ['errornode1', 'errornode2']
        node = nodes.PSErrorNode(testJid, self.mockPSClient)
        node.errorChannels = Mock(side_effect=utils.good_side_effect(errors))
        
        el = Element(('top', 'ns'))
        el.addContent('im covered in bees')
        el.toXml = Mock()
        d = node.onError(el)

        def cb(msg):
            self.assertEquals(self.mockPSClient.publish.call_count, 2)
            self.assertEquals(el.toXml.call_count, 0)

        d.addCallback(cb)
        return d 

    def test_onError_toPublishErrored(self):
        self.mockPSClient.publish = Mock(side_effect=utils.bad_side_effect(error.StanzaError('DISAPPOINTED')))
        errors = ['errornode1', 'errornode2', 'log']
        node = nodes.PSErrorNode(testJid, self.mockPSClient)
        node.errorChannels = Mock(side_effect=utils.good_side_effect(errors))
        
        el = Element(('top', 'ns'))
        el.addContent('im covered in bees')
        el.toXml = Mock()
        d = node.onError(el)

        def cb(msg):
            self.assertEquals(self.mockPSClient.publish.call_count, 2)
            self.assertEquals(el.toXml.call_count, 1)

        d.addCallback(cb)
        return self.assertFailure(d, error.StanzaError)
   

class NonTrippingLoadBalancerTests(unittest.TestCase):

    timeout = 2

    def setUp(self):
        self.mockPSClient = Mock()
        self.node = nodes.PSInputNode(testJid, self.mockPSClient)
        self.node.removeInput = Mock(side_effect=utils.good_side_effect('lush'))
        self.node.addInput = Mock(side_effect=utils.good_side_effect('lush'))
        self.sch = utils.ClockScheduler(task.Clock())
        
    def tearDown(self):
        pass

    def _makeLoader(self):
        loader = nodes.NonTrippingLoadBalancer()
        loader.coop = task.Cooperator(scheduler=self.sch.callLater)
        return loader
        
    def test_suspendAll(self):
        inputs = set(['1','2','3','4'])
        self.node.inputChannels = Mock(side_effect=utils.good_side_effect(inputs))
        loader = self._makeLoader()
        d = loader.suspendAll(self.node)

        def check(data):
            self.assertEquals(self.node.inputChannels.call_count, 1)
            self.assertEquals(data, set(['1','2','3','4']))
            self.assertEquals(self.node.removeInput.call_count, 4)
            self.assertFalse(self.node.addInput.called)

        d.addCallback(check)
        self.sch.clock.pump([1,1,1,1])
        return d
        
    def test_suspendAll_cantRemoveInput(self):
        inputs = set(['1','2','3','4'])
        self.node.inputChannels = Mock(side_effect=utils.good_side_effect(inputs))
        self.node.removeInput.side_effect = utils.bad_side_effect(ValueError('%s: removeInput failed' % self.__class__))
        loader = self._makeLoader()
        d = loader.suspendAll(self.node)

        def check(data):
            self.assertEquals(self.node.inputChannels.call_count, 1)
            self.assertEquals(data, set())
            self.assertEquals(self.node.removeInput.call_count, 4)
            self.assertFalse(self.node.addInput.called)

        d.addCallback(check)
        self.sch.clock.pump([1,1,1,1])
        return d
        
    def test_reloadAll(self):
        loader = self._makeLoader()
        d = loader.reloadAll(self.node, set(['1','2','3','4']))

        def check(data):
            self.assertEquals(data, set(['1','2','3','4']))
            self.assertEquals(self.node.addInput.call_count, 4)
            self.assertFalse(self.node.removeInput.called)

        d.addCallback(check)
        self.sch.clock.pump([1,1,1,1])
        return d
        
    def test_reloadAll_cantAddInput(self):
        old_inputs = set(['1','2','3','4'])
        self.node.addInput.side_effect = utils.bad_side_effect(ValueError('%s: addInput failed' % self.__class__))

        loader = self._makeLoader()
        d = loader.reloadAll(self.node, old_inputs)

        def check(data):
            self.assertEquals(data, set())
            self.assertEquals(self.node.addInput.call_count, 4)
            self.assertFalse(self.node.removeInput.called)

        d.addCallback(check)
        self.sch.clock.pump([1,1,1,1])
        return d
        
