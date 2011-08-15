# Copyright (c) Simon Parry.
# See LICENSE for details.

# tests for the pages module
from mock import Mock
from twisted.internet import defer
from twisted.trial import unittest
from twisted.words.protocols.jabber import jid
from twisted.words.xish.domish import Element
from wokkel import data_form, disco

import collab
from collab import pages
from collab.command import Command
from collab.test import utils


testJid = jid.JID('test@master.local')
        
class PagesTests(unittest.TestCase):

    timeout = 2

    def iq(self):
        iq = Element((None, 'iq'))
        iq['type'] = 'set'
        iq['to'] = 'responder@master.local'
        iq['from'] = 'requester@master.local'
        iq['id'] = 'id1'
        return iq

    def setUp(self):
        c = Command(node='input', action='execute')
        self.cmd_in = self.iq()
        self.cmd_in.addChild(c.toElement())
        self.getRegistered = Mock(side_effect=utils.good_side_effect(set(['master.local', 'mini.local'])))
        self.getComponents = Mock(side_effect=utils.good_side_effect(collab.COLLAB_COMPONENTS))

        psnodes = disco.DiscoItems()
        [psnodes.append(disco.DiscoItem(testJid, nid)) for nid in set(['master.local', 'mini.local'])]
        self.getPSNodes = Mock(side_effect=utils.good_side_effect(psnodes))

        self.people = ['test1@master.local', 'test2@master.local']
        jids = disco.DiscoItems()
        [jids.append(disco.DiscoItem(jid.JID(j))) for j in self.people]
        self.getAdmins = self.getPubs = self.getSubs = Mock(side_effect=utils.good_side_effect(jids))
        
    def tearDown(self):
        pass

    def test_CommandPage(self):
        c = Command(node='node', status='executing')
        p = pages.CommandPage(c)

        el = p.renderToElement(self.cmd_in, None)
        def checkIt(el):
            self.assertEquals(c.toElement().toXml(), el.toXml())

        el.addCallback(checkIt)
        return el

    @defer.inlineCallbacks
    def test_RegisterMachinePage(self):
        p = pages.RegisterMachinePage(self.getRegistered)
        el = yield p.renderToElement(self.cmd_in, None)
        cmd = Command.fromElement(el)

        self.assertTrue(self.getRegistered.called)
        self.assertTrue(cmd.actions is not None)
        self.assertTrue(cmd.form is not None)

        form = data_form.findForm(cmd.toElement(), collab.COLLAB_NS)
        self.assertTrue(form is not None)
        self.assertTrue('machine' in form.fields)
        self.assertEquals(form.fields['machine'].fieldType, 'text-single')

    @defer.inlineCallbacks
    def test_UnregisterMachinePage(self):
        p = pages.UnregisterMachinePage(self.getRegistered)
        el = yield p.renderToElement(self.cmd_in, None)
        cmd = Command.fromElement(el)

        self.assertTrue(self.getRegistered.called)
        self.assertTrue(cmd.actions is not None)
        self.assertTrue(cmd.form is not None)

        form = data_form.findForm(cmd.toElement(), collab.COLLAB_NS)
        self.assertTrue(form is not None)
        self.assertTrue('machines' in form.fields)
        self.assertEquals(form.fields['machines'].fieldType, 'list-multi')

    @defer.inlineCallbacks
    def test_CreateCollabNodePage(self):
        p = pages.CreateCollabNodePage(self.getRegistered, self.getComponents)
        el = yield p.renderToElement(self.cmd_in, None)
        cmd = Command.fromElement(el)

        self.assertTrue(self.getRegistered.called)
        self.assertTrue(self.getComponents.called)
        self.assertTrue(cmd.actions is not None)
        self.assertTrue(cmd.form is not None)

        form = data_form.findForm(cmd.toElement(), collab.COLLAB_NS)
        self.assertTrue(form is not None)
        self.assertTrue('component' in form.fields)
        self.assertTrue('machine' in form.fields)
        self.assertEquals(form.fields['component'].fieldType, 'list-single')
        self.assertEquals(form.fields['machine'].fieldType, 'list-single')        

    @defer.inlineCallbacks
    def test_CreatePubsubNodePage(self):
        p = pages.CreatePubsubNodePage(self.getComponents)
        el = yield p.renderToElement(self.cmd_in, None)
        cmd = Command.fromElement(el)

        self.assertTrue(self.getComponents.called)
        self.assertTrue(cmd.actions is not None)
        self.assertTrue(cmd.form is not None)

        form = data_form.findForm(cmd.toElement(), collab.COLLAB_NS)
        self.assertTrue(form is not None)
        self.assertTrue('component' in form.fields)
        self.assertTrue('name' in form.fields)
        self.assertEquals(form.fields['component'].fieldType, 'list-single')
        self.assertEquals(form.fields['name'].fieldType, 'text-single')        

    @defer.inlineCallbacks
    def test_InplaceConfigurePubsubNodePage(self):
        p = pages.InplaceConfigurePubsubNodePage(self.getPSNodes)
        el = yield p.renderToElement(self.cmd_in, None)
        cmd = Command.fromElement(el)

        self.assertTrue(self.getPSNodes.called)
        self.assertTrue(cmd.actions is not None)
        self.assertTrue(cmd.form is not None)

        form = data_form.findForm(cmd.toElement(), collab.COLLAB_NS)
        self.assertTrue(form is not None)
        self.assertTrue('name' in form.fields)
        self.assertEquals(form.fields['name'].fieldType, 'list-single')        

    @defer.inlineCallbacks
    def test_ConfigurePubsubNodeOwnersPage(self):
        p = pages.ConfigurePubsubNodeOwnersPage(self.getAdmins)
        p._getOptions = Mock(return_value=[])
        testState = {'name': 'george'}
        
        el = yield p.renderToElement(self.cmd_in, testState)
        cmd = Command.fromElement(el)

        self.assertTrue(self.getAdmins.called)
        self.assertTrue(p._getOptions.called)
        self.assertTrue(cmd.actions is not None)
        self.assertTrue(cmd.form is not None)

        form = data_form.findForm(cmd.toElement(), collab.COLLAB_NS)
        self.assertTrue(form is not None)
        self.assertTrue('admins' in form.fields)
        self.assertEquals(form.fields['admins'].fieldType, 'list-multi')        

    def test_ConfigurePubsubNodeOwnersPage_getOptions(self):
        p = pages.ConfigurePubsubNodeOwnersPage(self.getAdmins)

        admins = disco.DiscoItems()
        admins.append(disco.DiscoItem(jid.JID('test@master.local')))
        options = p._getOptions(admins)
        self.assertEquals(
            options[0].toElement().toXml(),
            data_form.Option(jid.JID('test@master.local').full()).toElement().toXml()
            )

    @defer.inlineCallbacks
    def test_ConfigurePubsubNodePublishersPage(self):
        p = pages.ConfigurePubsubNodePublishersPage(self.getPubs)
        p._getOptions = Mock(return_value=[])
        testState = {'name': 'george', 'admins': []}
        
        el = yield p.renderToElement(self.cmd_in, testState)
        cmd = Command.fromElement(el)

        self.assertTrue(self.getPubs.called)
        self.assertTrue(p._getOptions.called)
        self.assertTrue(cmd.actions is not None)
        self.assertTrue(cmd.form is not None)

        form = data_form.findForm(cmd.toElement(), collab.COLLAB_NS)
        self.assertTrue(form is not None)
        self.assertTrue('publishers' in form.fields)
        self.assertEquals(form.fields['publishers'].fieldType, 'list-multi')        
    
    def test_ConfigurePubsubNodePublishersPage_getOptions(self):
        p = pages.ConfigurePubsubNodePublishersPage(self.getPubs)

        admins = set(['test@master.local'])
        pubs = disco.DiscoItems()
        pubs.append(disco.DiscoItem(jid.JID('test@master.local')))
        options = p._getOptions(pubs, admins)
        self.assertEquals(options, [])

        admins = set(['test@master.local'])
        pubs = disco.DiscoItems()
        pubs.append(disco.DiscoItem(jid.JID('new@master.local')))
        options = p._getOptions(pubs, admins)
        self.assertEquals(
            options[0].toElement().toXml(),
            data_form.Option(jid.JID('new@master.local').full()).toElement().toXml()
            )

    @defer.inlineCallbacks
    def test_ConfigurePubsubNodeSubscribersPage(self):
        p = pages.ConfigurePubsubNodeSubscribersPage(self.getSubs)
        p._getOptions = Mock(return_value=[])
        testState = {'name': 'george', 'admins': [], 'publishers': []}
        
        el = yield p.renderToElement(self.cmd_in, testState)
        cmd = Command.fromElement(el)

        self.assertTrue(self.getSubs.called)
        self.assertTrue(p._getOptions.called)
        self.assertTrue(cmd.actions is not None)
        self.assertTrue(cmd.form is not None)

        form = data_form.findForm(cmd.toElement(), collab.COLLAB_NS)
        self.assertTrue(form is not None)
        self.assertTrue('subscribers' in form.fields)
        self.assertEquals(form.fields['subscribers'].fieldType, 'list-multi')        

    def test_ConfigurePubsubNodeSubscribersPage_getOptions(self):
        p = pages.ConfigurePubsubNodeSubscribersPage(self.getPubs)

        admins = set(['test@master.local'])
        pubs = set(['test1@master.local'])
        subs = disco.DiscoItems()
        subs.append(disco.DiscoItem(jid.JID('test@master.local')))
        options = p._getOptions(subs, pubs, admins)
        self.assertEquals(options, [])

        admins = set(['test@master.local'])
        pubs = set(['test1@master.local'])
        subs = disco.DiscoItems()
        subs.append(disco.DiscoItem(jid.JID('test1@master.local')))
        options = p._getOptions(subs, pubs, admins)
        self.assertEquals(options, [])

        admins = set(['test@master.local'])
        pubs = set(['test1@master.local'])
        subs = disco.DiscoItems()
        subs.append(disco.DiscoItem(jid.JID('new@master.local')))
        options = p._getOptions(subs, pubs, admins)
        self.assertEquals(
            options[0].toElement().toXml(),
            data_form.Option(jid.JID('new@master.local').full()).toElement().toXml()
            )

    @defer.inlineCallbacks
    def test_DeletePubsubNodePage(self):
        yield None
    
    @defer.inlineCallbacks
    def test_EndPage(self):
        p = pages.EndPage('Im beginning to see the light')
        el = yield p.renderToElement(self.cmd_in, None)
        cmd = Command.fromElement(el)

        self.assertTrue(cmd.actions is None)
        self.assertTrue(cmd.form is None)
        self.assertEquals(len(cmd.notes), 1)
        self.assertEquals(cmd.notes[0].content, 'Im beginning to see the light')

    @defer.inlineCallbacks
    def test_ViewCollabChannelsPage(self):
        yield None

    @defer.inlineCallbacks
    def test_ConfigureCollabNodeLoadBalancerPage(self):
        p = pages.ConfigureCollabNodeLoadBalancerPage()
        el = yield p.renderToElement(self.cmd_in, None)
        cmd = Command.fromElement(el)

        self.assertTrue(cmd.actions is not None)
        self.assertTrue(cmd.form is not None)

        form = data_form.findForm(cmd.toElement(), collab.COLLAB_NS)
        self.assertTrue(form is not None)
        self.assertTrue('frequency' in form.fields)
        self.assertEquals(form.fields['frequency'].fieldType, 'text-single')

    @defer.inlineCallbacks
    def test_LHPPortfoliosPage(self):
        yield None

