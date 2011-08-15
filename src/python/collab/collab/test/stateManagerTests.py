# Copyright (c) Simon Parry.
# See LICENSE for details.

#tests for stateManager module
from mock import Mock, patch
from twisted.internet import defer, task
from twisted.trial import unittest
from twisted.words.protocols.jabber import jid, error

from collab import stateManager as sm, nodes
from collab.test import utils


testJid = jid.JID('test@master.local')

class StateChangerBaseTests(unittest.TestCase):

    timeout = 2

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_add_required(self):
        sc = sm.StateChangerBase(requiredFields=['component', 'machine'])
        sc.add(field='component', val='flux capacitor')

        self.assertTrue('component' in sc.data)
        self.assertEquals(sc.data['component'], 'flux capacitor')

    def test_add_notrequired(self):
        sc = sm.StateChangerBase(requiredFields=['component', 'machine'])
        sc.add(field='gigawatts', val=1.21)

        self.assertTrue('gigawatts' not in sc.data)

    def test_add_overwrites(self):
        sc = sm.StateChangerBase(requiredFields=['component', 'machine'])
        sc.add(field='component', val='flux capacitor')
        self.assertTrue('component' in sc.data)
        self.assertEquals(sc.data['component'], 'flux capacitor')

        sc.add(field='component', val='plutonium chamber')
        self.assertTrue('component' in sc.data)
        self.assertEquals(sc.data['component'], 'plutonium chamber')
        
    def test_isValid(self):
        sc = sm.StateChangerBase(requiredFields=['component', 'machine'])
        sc.add(field='component', val='flux capacitor')
        sc.add(field='machine', val='delorian')

        self.assertTrue(sc.isValid())

    def test_isInvalid(self):
        sc = sm.StateChangerBase(requiredFields=['component', 'machine'])
        sc.add(field='component', val='flux capacitor')

        self.assertFalse(sc.isValid())

    def test_reset(self):
        sc = sm.StateChangerBase(requiredFields=['component', 'machine'])
        sc.add(field='component', val='flux capacitor')
        sc.reset()

        self.assertFalse(sc.isValid())
        self.assertFalse('component' in sc.data)

        
class RegisterMachineStateChangerTests(unittest.TestCase):

    timeout = 2

    def setUp(self):
        self.xmlrpc = Mock()
        self.xmlrpc.host_register = Mock()

    def tearDown(self):
        pass

    def test_commit(self):
        sc = sm.RegisterMachineStateChanger(self.xmlrpc)
        sc.data['machine'] = 'testmachine'
        d = sc.commit()

        def check(val):
            self.xmlrpc.host_register.assert_called_once_with({'host': 'testmachine'})

        d.addCallback(check)
        return d
        
class UnregisterMachineStateChangerTests(unittest.TestCase):

    timeout = 2

    def setUp(self):
        self.xmlrpc = Mock()
        self.xmlrpc.host_remove = Mock()

    def tearDown(self):
        pass

    def test_commit(self):
        sc = sm.UnregisterMachineStateChanger(self.xmlrpc)
        sc.data['machines'] = ['testmachine1', 'testmachine2']
        d = sc.commit()

        def check(val):
            self.assertEquals(self.xmlrpc.host_remove.call_count, 2)
            self.assertEquals(self.xmlrpc.host_remove.call_args_list[0], (({'host': 'testmachine1'},), {}))
            self.assertEquals(self.xmlrpc.host_remove.call_args_list[1], (({'host': 'testmachine2'},), {}))

        d.addCallback(check)
        return d


class CreateCollabNodeStateChangerTests(unittest.TestCase):
    pass


import collab
class ManageAffiliationsTests(unittest.TestCase):

    timeout = 2

    def setUp(self):
        self.sender = jid.JID('sender@master.local')
        
        self.old_affiliations = {
            jid.JID('test1@master.local'): 'publisher',
            jid.JID('test2@master.local'): 'none',
            }

        self.ignored_affiliations = {
            self.sender: 'owner',
            jid.JID(collab.ADMIN_JID): 'owner',
            }

        self.pubs = ['pubs1@master.local', 'pubs2@master.local']
        self.admins = ['admins1@master.local', 'admins2@master.local']

    def tearDown(self):
        pass

    @patch('collab.pubsubRequestWithAffiliations.getAffiliations')
    @patch('collab.pubsubRequestWithAffiliations.makeAffiliations')
    def test_manageAffiliations_onlyOldAffiliations(self, makeAffiliationsMock, getAffiliationsMock):
        getAffiliationsMock.side_effect = utils.good_side_effect(self.old_affiliations)
        makeAffiliationsMock.side_effect = utils.good_side_effect('lush')
        sender = self.sender
        name = 'name'
        xsMock = Mock()
        d = sm.manageAffiliations(sender, name, [], [], xsMock)
        
        def cb(msg):
            getAffiliationsMock.assert_called_once_with(sender=sender, node=name, xs=xsMock)
            new_affiliations = {
                jid.JID('test1@master.local').full(): 'none',
                jid.JID('test2@master.local').full(): 'none',
            }

            makeAffiliationsMock.assert_called_once_with(
                sender=sender, node=name, affiliations=new_affiliations, xs=xsMock
                )

        d.addCallback(cb)
        return d
        
    @patch('collab.pubsubRequestWithAffiliations.getAffiliations')
    @patch('collab.pubsubRequestWithAffiliations.makeAffiliations')
    def test_manageAffiliations_onlyIgnoredOldAffiliations(self, makeAffiliationsMock, getAffiliationsMock):
        getAffiliationsMock.side_effect = utils.good_side_effect(self.ignored_affiliations)
        makeAffiliationsMock.side_effect = utils.good_side_effect('lush')
        sender = self.sender
        name = 'name'
        xsMock = Mock()
        d = sm.manageAffiliations(sender, name, [], [], xsMock)
        
        def cb(msg):
            getAffiliationsMock.assert_called_once_with(sender=sender, node=name, xs=xsMock)
            self.assertEquals(makeAffiliationsMock.call_count, 0)

        d.addCallback(cb)
        return d
        
    @patch('collab.pubsubRequestWithAffiliations.getAffiliations')
    @patch('collab.pubsubRequestWithAffiliations.makeAffiliations')
    def test_manageAffiliations_OnlyPubs(self, makeAffiliationsMock, getAffiliationsMock):
        getAffiliationsMock.side_effect = utils.good_side_effect({})
        makeAffiliationsMock.side_effect = utils.good_side_effect('lush')
        sender = self.sender
        name = 'name'
        xsMock = Mock()
        d = sm.manageAffiliations(sender, name, self.pubs, [], xsMock)
        
        def cb(msg):
            new_affiliations = dict([(p, 'publisher') for p in self.pubs])
            getAffiliationsMock.assert_called_once_with(sender=sender, node=name, xs=xsMock)
            makeAffiliationsMock.assert_called_once_with(
                sender=sender, node=name, affiliations=new_affiliations, xs=xsMock
                )
            

        d.addCallback(cb)
        return d
        
    @patch('collab.pubsubRequestWithAffiliations.getAffiliations')
    @patch('collab.pubsubRequestWithAffiliations.makeAffiliations')
    def test_manageAffiliations_OnlyIgnoredPubs(self, makeAffiliationsMock, getAffiliationsMock):
        getAffiliationsMock.side_effect = utils.good_side_effect({})
        makeAffiliationsMock.side_effect = utils.good_side_effect('lush')
        sender = self.sender
        name = 'name'
        xsMock = Mock()
        d = sm.manageAffiliations(sender, name, [self.sender.full()], [], xsMock)
        
        def cb(msg):
            getAffiliationsMock.assert_called_once_with(sender=sender, node=name, xs=xsMock)
            self.assertEquals(makeAffiliationsMock.call_count, 0)

        d.addCallback(cb)
        return d
        
    @patch('collab.pubsubRequestWithAffiliations.getAffiliations')
    @patch('collab.pubsubRequestWithAffiliations.makeAffiliations')
    def test_manageAffiliations_OnlyAdmins(self, makeAffiliationsMock, getAffiliationsMock):
        getAffiliationsMock.side_effect = utils.good_side_effect({})
        makeAffiliationsMock.side_effect = utils.good_side_effect('lush')
        sender = self.sender
        name = 'name'
        xsMock = Mock()
        d = sm.manageAffiliations(sender, name, [], self.admins, xsMock)
        
        def cb(msg):
            new_affiliations = dict([(p, 'owner') for p in self.admins])
            getAffiliationsMock.assert_called_once_with(sender=sender, node=name, xs=xsMock)
            makeAffiliationsMock.assert_called_once_with(
                sender=sender, node=name, affiliations=new_affiliations, xs=xsMock
                )
            
        d.addCallback(cb)
        return d
        
    @patch('collab.pubsubRequestWithAffiliations.getAffiliations')
    @patch('collab.pubsubRequestWithAffiliations.makeAffiliations')
    def test_manageAffiliations_OnlyIgnoredAdmins(self, makeAffiliationsMock, getAffiliationsMock):
        getAffiliationsMock.side_effect = utils.good_side_effect({})
        makeAffiliationsMock.side_effect = utils.good_side_effect('lush')
        sender = self.sender
        name = 'name'
        xsMock = Mock()
        d = sm.manageAffiliations(sender, name, [], [self.sender.full()], xsMock)
        
        def cb(msg):
            getAffiliationsMock.assert_called_once_with(sender=sender, node=name, xs=xsMock)
            self.assertEquals(makeAffiliationsMock.call_count, 0)

        d.addCallback(cb)
        return d
        
    @patch('collab.pubsubRequestWithAffiliations.getAffiliations')
    @patch('collab.pubsubRequestWithAffiliations.makeAffiliations')
    def test_manageAffiliations_includeAdmin(self, makeAffiliationsMock, getAffiliationsMock):
        getAffiliationsMock.side_effect = utils.good_side_effect({})
        makeAffiliationsMock.side_effect = utils.good_side_effect('lush')
        sender = self.sender
        name = 'name'
        xsMock = Mock()
        d = sm.manageAffiliations(sender, name, [], [self.sender.full()], xsMock, True)
        
        def cb(msg):
            new_affiliations = {collab.ADMIN_JID: 'owner'}
            getAffiliationsMock.assert_called_once_with(sender=sender, node=name, xs=xsMock)
            makeAffiliationsMock.assert_called_once_with(
                sender=sender, node=name, affiliations=new_affiliations, xs=xsMock
                )
            
        d.addCallback(cb)
        return d
        
from wokkel import pubsub as ps
class ManageSubscriptionsTests(unittest.TestCase):

    timeout = 2

    def setUp(self):
        self.sender = jid.JID('sender@master.local')

        self.old_subscriptions = set([
            ps.Subscription(
                nodeIdentifier=None,
                subscriber=jid.JID('test1@master.local'),
                state='subscribed',
                subscriptionIdentifier=1
                ),
            ps.Subscription(
                nodeIdentifier=None,
                subscriber=jid.JID('test2@master.local'),
                state='subscribed',
                subscriptionIdentifier=2
                )
            ])

        self.subscriptions = ['sub1@master.local', 'sub2@master.local']

    def tearDown(self):
        pass

    @patch('collab.pubsubRequestWithAffiliations.getSubscriptions')
    @patch('collab.pubsubRequestWithAffiliations.makeSubscriptions')
    def test_manageSubscriptions_oldSubsOnly(self, makeSubscriptionsMock, getSubscriptionsMock):
        getSubscriptionsMock.side_effect = utils.good_side_effect(self.old_subscriptions)
        makeSubscriptionsMock.side_effect = utils.good_side_effect('lush')
        sender = self.sender
        name = 'name'
        xsMock = Mock()
        d = sm.manageSubscriptions(sender, name, [], xsMock)
        
        def cb(msg):
            getSubscriptionsMock.assert_called_once_with(sender=sender, node=name, xs=xsMock)
            self.assertEquals(makeSubscriptionsMock.call_count, 1)
            args = makeSubscriptionsMock.call_args[1]
            self.assertEquals(args['sender'], sender)
            self.assertEquals(args['node'], name)
            self.assertEquals(args['xs'], xsMock)
            for s in args['subscriptions']:
                self.assertEquals(s.state, 'none')
                self.assertTrue(s.subscriber == jid.JID('test1@master.local') or jid.JID('test2@master.local'))
            
        d.addCallback(cb)
        return d

    @patch('collab.pubsubRequestWithAffiliations.getSubscriptions')
    @patch('collab.pubsubRequestWithAffiliations.makeSubscriptions')
    def test_manageSubscriptions_newSubsOnly(self, makeSubscriptionsMock, getSubscriptionsMock):
        getSubscriptionsMock.side_effect = utils.good_side_effect(set())
        makeSubscriptionsMock.side_effect = utils.good_side_effect('lush')
        sender = self.sender
        name = 'name'
        xsMock = Mock()
        d = sm.manageSubscriptions(sender, name, self.subscriptions, xsMock)
        
        def cb(msg):
            getSubscriptionsMock.assert_called_once_with(sender=sender, node=name, xs=xsMock)
            self.assertEquals(makeSubscriptionsMock.call_count, 1)
            args = makeSubscriptionsMock.call_args[1]
            self.assertEquals(args['sender'], sender)
            self.assertEquals(args['node'], name)
            self.assertEquals(args['xs'], xsMock)
            for s in args['subscriptions']:
                self.assertEquals(s.state, 'subscribed')
                self.assertTrue(s.subscriber == jid.JID('sub1@master.local') or jid.JID('sub2@master.local'))
            
        d.addCallback(cb)
        return d

class MakePSNodeTests(unittest.TestCase):

    timeout = 2

    def setUp(self):
        self.sender = jid.JID('sender@master.local')
        self.psclient = Mock()

    def tearDown(self):
        pass

    def test_makePSNode_okName(self):
        name = 'ok name'
        self.psclient.createNode = Mock(side_effect=utils.good_side_effect('lush'))        

        d = sm.makePSNode(self.sender, name, self.psclient)

        def cb(msg):
            self.assertEquals(msg, name)
            self.assertEquals(self.psclient.createNode.call_count, 1)

        d.addCallback(cb)
        return d

    def test_makePSNode_badName(self):
        name = 'bad name'
        self.psclient.createNode = Mock(side_effect=utils.bad_side_effect(error.StanzaError(
            condition='conflict', text='%s: not lush' % self.__class__)))        

        d = sm.makePSNode(self.sender, name, self.psclient, 3)

        def cb(msg):
            self.assertTrue(False)
            
        def eb(msg):
            self.assertNotEquals(msg, name)
            self.assertEquals(self.psclient.createNode.call_count, 3)

        d.addCallbacks(cb, eb)
        return d


import gc
class CreatePubsubNodeStateChangerTests(unittest.TestCase):

    timeout = 2

    def setUp(self):
        self.psclient = Mock()
        self.psclient.xmlstream = Mock()
        self.jid = jid.JID('sender@master.local')

        self.comp = 'jelly bean factory'
        self.name = 'gerald'
        self.admins = ['admins1@master.local', 'admins2@master.local']
        self.pubs = ['pubs1@master.local', 'pubs2@master.local']
        self.subs = ['subs1@master.local', 'subs2@master.local']
        
    def tearDown(self):
        pass

    @patch('collab.stateManager.manageSubscriptions')
    @patch('collab.stateManager.manageAffiliations')
    @patch('collab.stateManager.makePSNode')
    def test_commit_ok(self, makePSNodeMock, manageAffiliationsMock, manageSubscriptionsMock):
        makePSNodeMock.side_effect = utils.good_side_effect(self.name)
        manageAffiliationsMock.side_effect = utils.good_side_effect('lush')
        manageSubscriptionsMock.side_effect = utils.good_side_effect('lush')

        sc = sm.CreatePubsubNodeStateChanger(self.psclient, self.jid)
        sc.data['component'] = self.comp
        sc.data['name'] = self.name
        sc.data['admins'] = self.admins
        sc.data['publishers'] = self.pubs
        sc.data['subscribers'] = self.subs

        d = sc.commit()

        def cb(ret):
            makePSNodeMock.assert_called_once_with(self.jid, self.name, self.psclient)
            manageAffiliationsMock.assert_called_once_with(
                self.jid, self.name, self.pubs, self.admins, self.psclient.xmlstream, True
                )
            manageSubscriptionsMock.assert_called_once_with(
                self.jid, self.name, self.subs, self.psclient.xmlstream
                )

        d.addCallback(cb)
        return d

    @patch('collab.stateManager.manageSubscriptions')
    @patch('collab.stateManager.manageAffiliations')
    @patch('collab.stateManager.makePSNode')
    def test_commit_cannotCreatePSNode(self, makePSNodeMock, manageAffiliationsMock, manageSubscriptionsMock):
        makePSNodeMock.side_effect = utils.bad_side_effect(error.StanzaError('%s: bleergh' % self.__class__))
        manageAffiliationsMock.side_effect = utils.good_side_effect('lush')
        manageSubscriptionsMock.side_effect = utils.good_side_effect('lush')

        sc = sm.CreatePubsubNodeStateChanger(self.psclient, self.jid)
        sc.data['component'] = self.comp
        sc.data['name'] = self.name
        sc.data['admins'] = self.admins
        sc.data['publishers'] = self.pubs
        sc.data['subscribers'] = self.subs

        d = sc.commit()

        def cb(ret):
            self.assertTrue(False)

        def eb(err):
            self.assertEquals(makePSNodeMock.call_count, 1)
            self.assertEquals(manageAffiliationsMock.call_count, 0)
            self.assertEquals(manageSubscriptionsMock.call_count, 0)

        d.addCallbacks(cb, eb)
        return d

    @patch('collab.stateManager.manageSubscriptions')
    @patch('collab.stateManager.manageAffiliations')
    @patch('collab.stateManager.makePSNode')
    def test_commit_cannotManageAffiliations(self, makePSNodeMock, manageAffiliationsMock, manageSubscriptionsMock):
        makePSNodeMock.side_effect = utils.good_side_effect('lush')
        manageAffiliationsMock.side_effect = utils.bad_side_effect(error.StanzaError('%s: bleergh' % self.__class__))
        manageSubscriptionsMock.side_effect = utils.good_side_effect('lush')

        sc = sm.CreatePubsubNodeStateChanger(self.psclient, self.jid)
        sc.data['component'] = self.comp
        sc.data['name'] = self.name
        sc.data['admins'] = self.admins
        sc.data['publishers'] = self.pubs
        sc.data['subscribers'] = self.subs

        d = sc.commit()
        # d is a deferredlist with errors in it so collect all
        # garbage and then check that the expected error is there
        # then make sure that the other stuff still happened
        gc.collect()
        self.assertEquals(len(self.flushLoggedErrors(error.StanzaError)), 1)
        self.assertEquals(makePSNodeMock.call_count, 1)
        self.assertEquals(manageAffiliationsMock.call_count, 1)
        self.assertEquals(manageSubscriptionsMock.call_count, 1)

    @patch('collab.stateManager.manageSubscriptions')
    @patch('collab.stateManager.manageAffiliations')
    @patch('collab.stateManager.makePSNode')
    def test_commit_cannotManageSubscriptions(self, makePSNodeMock, manageAffiliationsMock, manageSubscriptionsMock):
        makePSNodeMock.side_effect = utils.good_side_effect('lush')
        manageAffiliationsMock.side_effect = utils.good_side_effect('lush')
        manageSubscriptionsMock.side_effect = utils.bad_side_effect(error.StanzaError('%s: bleergh' % self.__class__))

        sc = sm.CreatePubsubNodeStateChanger(self.psclient, self.jid)
        sc.data['component'] = self.comp
        sc.data['name'] = self.name
        sc.data['admins'] = self.admins
        sc.data['publishers'] = self.pubs
        sc.data['subscribers'] = self.subs

        d = sc.commit()
        # d is a deferredlist with errors in it so collect all
        # garbage and then check that the expected error is there
        # then make sure that the other stuff still happened
        gc.collect()
        self.assertEquals(len(self.flushLoggedErrors(error.StanzaError)), 1)
        self.assertEquals(makePSNodeMock.call_count, 1)
        self.assertEquals(manageAffiliationsMock.call_count, 1)
        self.assertEquals(manageSubscriptionsMock.call_count, 1)

class ConfigPubsubNodeStateChangerTests(unittest.TestCase):

    timeout = 2

    def setUp(self):
        self.psclient = Mock()
        self.psclient.xmlstream = Mock()
        self.jid = jid.JID('sender@master.local')

        self.name = 'gerald'
        self.admins = ['admins1@master.local', 'admins2@master.local']
        self.pubs = ['pubs1@master.local', 'pubs2@master.local']
        self.subs = ['subs1@master.local', 'subs2@master.local']
        
    def tearDown(self):
        pass

    @patch('collab.stateManager.manageSubscriptions')
    @patch('collab.stateManager.manageAffiliations')
    def test_commit_ok(self, manageAffiliationsMock, manageSubscriptionsMock):
        manageAffiliationsMock.side_effect = utils.good_side_effect('lush')
        manageSubscriptionsMock.side_effect = utils.good_side_effect('lush')

        sc = sm.ConfigPubsubNodeStateChanger(self.psclient, self.jid)
        sc.data['name'] = self.name
        sc.data['admins'] = self.admins
        sc.data['publishers'] = self.pubs
        sc.data['subscribers'] = self.subs

        d = sc.commit()

        def cb(ret):
            manageAffiliationsMock.assert_called_once_with(
                self.jid, self.name, self.pubs, self.admins, self.psclient.xmlstream
                )
            manageSubscriptionsMock.assert_called_once_with(
                self.jid, self.name, self.subs, self.psclient.xmlstream
                )

        d.addCallback(cb)
        return d

    @patch('collab.stateManager.manageSubscriptions')
    @patch('collab.stateManager.manageAffiliations')
    def test_commit_cannotManageAffiliations(self, manageAffiliationsMock, manageSubscriptionsMock):
        manageAffiliationsMock.side_effect = utils.bad_side_effect(error.StanzaError('%s: bleergh' % self.__class__))
        manageSubscriptionsMock.side_effect = utils.good_side_effect('lush')

        sc = sm.ConfigPubsubNodeStateChanger(self.psclient, self.jid)
        sc.data['name'] = self.name
        sc.data['admins'] = self.admins
        sc.data['publishers'] = self.pubs
        sc.data['subscribers'] = self.subs

        d = sc.commit()
        # d is a deferredlist with errors in it so collect all
        # garbage and then check that the expected error is there
        # then make sure that the other stuff still happened
        gc.collect()
        self.assertEquals(len(self.flushLoggedErrors(error.StanzaError)), 1)
        self.assertEquals(manageAffiliationsMock.call_count, 1)
        self.assertEquals(manageSubscriptionsMock.call_count, 1)

    @patch('collab.stateManager.manageSubscriptions')
    @patch('collab.stateManager.manageAffiliations')
    def test_commit_cannotManageSubscriptions(self, manageAffiliationsMock, manageSubscriptionsMock):
        manageAffiliationsMock.side_effect = utils.good_side_effect('lush')
        manageSubscriptionsMock.side_effect = utils.bad_side_effect(error.StanzaError('%s: bleergh' % self.__class__))

        sc = sm.ConfigPubsubNodeStateChanger(self.psclient, self.jid)
        sc.data['name'] = self.name
        sc.data['admins'] = self.admins
        sc.data['publishers'] = self.pubs
        sc.data['subscribers'] = self.subs

        d = sc.commit()
        # d is a deferredlist with errors in it so collect all
        # garbage and then check that the expected error is there
        # then make sure that the other stuff still happened
        gc.collect()
        self.assertEquals(len(self.flushLoggedErrors(error.StanzaError)), 1)
        self.assertEquals(manageAffiliationsMock.call_count, 1)
        self.assertEquals(manageSubscriptionsMock.call_count, 1)


class DeletePubsubNodeStateChangerTests(unittest.TestCase):

    timeout = 2

    def setUp(self):
        self.psclient = Mock()
        self.psclient.deleteNode = Mock()
        self.jid = jid.JID('sender@master.local')

        self.names = ['gerald', 'henry']
        
    def tearDown(self):
        pass

    def test_commit_ok(self):
        self.psclient.deleteNode.side_effect = utils.good_side_effect('lush')
        sc = sm.DeletePubsubNodeStateChanger(self.psclient, self.jid)
        sc.data['name'] = self.names

        d = sc.commit()
        def cb(msg):
            self.assertEquals(self.psclient.deleteNode.call_count, 2)

        d.addCallback(cb)
        return d
        

class ConfigureLoadBalancerStateChangerTests(unittest.TestCase):

    timeout = 2

    def setUp(self):
        self.loader = Mock()
        self.loader.running = True
        self.loader.stop = Mock()
        self.loader.start = Mock()

    def tearDown(self):
        pass

    @defer.inlineCallbacks
    def test_ConfigureLoadBalancerStateChanger(self):
        changer = sm.ConfigureLoadBalancerStateChanger(self.loader)
        changer.data['frequency'] = '3.0'

        yield changer.commit()

        self.assertTrue(self.loader.stop.called)
        self.loader.start.assert_called_with(3.0)

    @defer.inlineCallbacks
    def test_ConfigureLoadBalancerStateChanger_notStarted(self):
        self.loader.running = False
        changer = sm.ConfigureLoadBalancerStateChanger(self.loader)
        changer.data['frequency'] = '3.0'

        yield changer.commit()

        self.assertFalse(self.loader.stop.called)
        self.loader.start.assert_called_with(3.0)

    @defer.inlineCallbacks
    def test_ConfigureLoadBalancerStateChanger_badFreq(self):
        changer = sm.ConfigureLoadBalancerStateChanger(self.loader)
        changer.data['frequency'] = '-3.0'

        yield changer.commit()

        self.loader.start.assert_called_with(1.0)


class LHPPortfolioStateChangerTests(unittest.TestCase):

    timeout = 2

    def setUp(self):
        self.broadcaster = Mock(side_effect=utils.good_side_effect('lush'))
        self.makePortfolioMock = Mock(return_value='not important')
        self.dp = '0.01'
        self.corr = '0.02'
        self.num_issuers = '3'
        self.num_runs = '100'

    def tearDown(self):
        pass

    def test_commit_ok(self):
        lhp = sm.LHPPortfolioStateChanger(self.broadcaster)
        lhp._makePortfolio = self.makePortfolioMock
        lhp.data['default_probability'] = self.dp
        lhp.data['base_correlation'] = self.corr
        lhp.data['number_issuers'] = self.num_issuers
        lhp.data['number_runs'] = self.num_runs

        d = lhp.commit()
        def cb(msg):
            lhp._makePortfolio.assert_called_once_with(0.02, 0.01, 3)
            self.assertEquals(lhp.broadcaster.call_count, 1)

        d.addCallback(cb)
        return d
        

class StateMergerTests(unittest.TestCase):

    timeout = 2

    def setUp(self):
        self.testState1 = dict([
            ('component', 'flux capacitor')
            ])
        self.testState2 = dict([
            ('machine', 'delorian')
            ])
        self.testState3 = dict([
            ('machine', 'liubot')
            ])
        
    def tearDown(self):
        pass

    def test_merge(self):
        merger = sm.StateMerger()
        
        merger.merge(self.testState1)
        self.assertEquals(merger.states, [{'component': 'flux capacitor'}])
        self.assertEquals(merger.data, {'component': 'flux capacitor'})

        merger.merge(self.testState2)
        self.assertEquals(merger.states,
                          [
                              {'component': 'flux capacitor'},
                              {'component': 'flux capacitor', 'machine': 'delorian'}
                          ])
        self.assertEquals(merger.data, {'component': 'flux capacitor', 'machine': 'delorian'})

        merger.merge(self.testState3)
        self.assertEquals(merger.states,
                          [
                              {'component': 'flux capacitor'},
                              {'component': 'flux capacitor', 'machine': 'delorian'},
                              {'component': 'flux capacitor', 'machine': 'liubot'}
                          ])
        self.assertEquals(merger.data, {'component': 'flux capacitor', 'machine': 'liubot'})

    def test_reset(self):
        merger = sm.StateMerger()
        
        merger.merge(self.testState1)
        merger.reset()
        self.assertEquals(merger.states, [])
        self.assertEquals(merger.data, {})


class StateManagerTests(unittest.TestCase):

    timeout = 2

    def setUp(self):
        self.testState = dict([
            ('component', 'flux capacitor'),
            ('machine', 'delorian')
            ])
        
        self.validChanger = sm.StateChangerBase(['component', 'machine'])
        self.validChanger.isValid = Mock(return_value=True)
        self.validChanger.commit = Mock()
        self.validChanger.reset = Mock()
        self.validChanger.add = Mock()

        self.invalidChanger = sm.StateChangerBase(['component', 'machine'])
        self.invalidChanger.isValid = Mock(return_value=False)
        self.invalidChanger.commit = Mock()
        self.invalidChanger.reset = Mock()
        self.invalidChanger.add = Mock()

        self.merger = sm.StateMerger()
        self.merger.merge = Mock()
        self.merger.reset = Mock()
        
    def tearDown(self):
        pass

    def test_reset(self):
        stm = sm.StateManager(self.validChanger, self.merger)
        stm.push(self.testState)

        stm.reset()
        self.assertEquals(self.merger.states, [])
        self.assertTrue(self.validChanger.reset.called)
        self.assertTrue(self.merger.reset.called)

    def test_head(self):
        stm = sm.StateManager(self.validChanger)
        stm.push(self.testState)

        self.assertEquals(stm.head(), self.testState)
        self.assertEquals(stm.stateMerger.states, [self.testState])

    def test_head_noneleft(self):
        stm = sm.StateManager(self.validChanger)
        def head():
            stm.head()
        self.assertRaises(sm.EmptyStateManagerError, head)
        
    def test_push(self):
        stm = sm.StateManager(self.validChanger, self.merger)
        stm.push(self.testState)

        self.merger.merge.assert_called_once_with(self.testState)

    @defer.inlineCallbacks
    def test_commit_valid(self):
        stm = sm.StateManager(self.validChanger)
        stm.push(self.testState)
        yield stm.commit()

        self.assertTrue(self.validChanger.add.called)
        self.assertTrue(self.validChanger.isValid.called)
        self.assertTrue(self.validChanger.commit.called)

    @defer.inlineCallbacks
    def test_commit_invalid(self):
        stm = sm.StateManager(self.invalidChanger)
        stm.push(self.testState)
        try:
            yield stm.commit()
        except sm.InvalidStateError as e:
            pass

        self.assertTrue(self.invalidChanger.isValid.called)
        self.assertTrue(self.invalidChanger.add.called)
        self.assertFalse(self.invalidChanger.commit.called)
        self.assertFalse(self.invalidChanger.reset.called)

    def test_penultimateState(self):
        stm = sm.StateManager(self.validChanger)
        testState2 = dict([
            ('emit', 'time'),
            ('levart', 'travel')
            ])
        stm.push(self.testState)
        stm.push(testState2)

        self.assertEquals(stm.penultimateState(), self.testState)
        self.assertEquals(stm.stateMerger.states, [])

    def test_penultimateState_noneleft(self):
        stm = sm.StateManager(self.validChanger)

        def pop():
            stm.penultimateState()
        self.assertRaises(sm.EmptyStateManagerError, pop)

    def test_penultimateState_oneleft(self):
        stm = sm.StateManager(self.validChanger)
        stm.push(self.testState)
        def pop():
            stm.penultimateState()
        self.assertRaises(sm.EmptyStateManagerError, pop)

        
