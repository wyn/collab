# Copyright (c) Simon Parry.
# See LICENSE for details.

#tests for stateManager module
from twisted.internet import defer
from twisted.trial import unittest
from twisted.words.protocols.jabber import jid
from twisted.words.xish.domish import Element
from wokkel import data_form

import collab
from collab.command import Command, Actions
from collab.pageManager import PageManager, PageManagerError
from collab.pages import CommandPage


testJid = jid.JID('test@master.local')
        
class PageManagerTests(unittest.TestCase):

    timeout = 2

    def setUp(self):
        def iq():
            iq = Element((None, 'iq'))
            iq['type'] = 'set'
            iq['to'] = 'responder@master.local'
            iq['from'] = 'requester@master.local'
            iq['id'] = 'id1'
            return iq

        def cancel():
            cmd = Element((collab.COMMAND_NS, 'command'))
            cmd['node'] = 'collabs_nodes_add'
            cmd['sessionid'] = 'sessionid1'
            cmd['action'] = 'cancel'
            return cmd

        def prev():
            cmd = Element((collab.COMMAND_NS, 'command'))
            cmd['node'] = 'collabs_nodes_add'
            cmd['sessionid'] = 'sessionid1'
            cmd['action'] = 'prev'
            return cmd

        def nex():
            cmd = Element((collab.COMMAND_NS, 'command'))
            cmd['node'] = 'collabs_nodes_add'
            cmd['sessionid'] = 'sessionid1'
            cmd['action'] = 'execute'
            return cmd

        def nex_start():
            cmd = Element((collab.COMMAND_NS, 'command'))
            cmd['node'] = 'collabs_nodes_add'
            cmd['action'] = 'execute'
            return cmd

        def result_iq():
            iq = Element((None, 'iq'))
            iq['type'] = 'result'
            iq['to'] = 'responder@master.local'
            iq['from'] = 'requester@master.local'
            iq['id'] = 'id1'
            return iq
            
        self.cancel_iq = iq()
        self.cancel_iq.addChild(cancel())

        self.prev_iq = iq()
        self.prev_iq.addChild(prev())

        self.cmd = Command(node='collabs_nodes_add', status='executing', sessionid='sessionid1')
        actions = Actions()
        actions.setDefault('next')
        self.cmd.set_actions(actions)

        form = data_form.Form(
            formType='form',
            title=u'Unregister a machine',
            instructions=[u'Please select the machine to be unregistered'],
            formNamespace=collab.COLLAB_NS
            )

        form.addField(data_form.Field(
            var = 'machine',
            label = u'Machine',
            desc = u'Please select a machine domain name',
            required = True,
            fieldType='list-multi',
            options = [data_form.Option(m) for m in set(['master.local', 'mini.local'])]
            ))
        self.cmd.set_form(form)

        self.next_iq = iq()
        cmd = self.next_iq.addChild(nex())
        x = cmd.addElement('x', defaultUri=data_form.NS_X_DATA)
        x['type'] = 'submit'
        field = x.addElement('field')
        field['var'] = 'service'
        field.addElement('value', content='something')

        self.next_start_iq = iq()
        self.next_start_iq.addChild(nex_start())

        self.state = dict({'one': 1})

    def tearDown(self):
        pass

    def test_PageManager_add_page(self):
        mngr = PageManager()
        p = CommandPage(self.cmd)
        mngr.add_page(p)
        self.assertEquals(len(mngr.pages), 1)
        self.assertEquals(mngr.pages[0], p)

    @defer.inlineCallbacks
    def test_PageManager_cancel_page(self):

        mngr = PageManager()
        mngr.index = 2
        iq = yield mngr.cancel_page(self.cancel_iq, self.state)

        self.assertEquals(mngr.index, 0)
        
        self.assertEquals(iq['to'], 'requester@master.local')
        self.assertEquals(iq['from'], 'responder@master.local')
        self.assertEquals(iq['id'], 'id1')
        self.assertEquals(iq['type'], 'result')

        cmd = iq.firstChildElement()
        self.assertEquals(cmd.defaultUri, collab.COMMAND_NS)
        self.assertEquals(cmd['sessionid'], 'sessionid1')
        self.assertEquals(cmd['node'], 'collabs_nodes_add')
        self.assertEquals(cmd['status'], 'canceled')

    @defer.inlineCallbacks
    def test_PageManager_prev_page(self):

        mngr = PageManager()
        mngr.add_page(CommandPage(self.cmd))
        mngr.index = 1
        iq = yield mngr.prev_page(self.prev_iq, self.state)

        self.assertEquals(mngr.index, 0)

        self.assertEquals(iq['to'], 'requester@master.local')
        self.assertEquals(iq['from'], 'responder@master.local')
        self.assertEquals(iq['id'], 'id1')
        self.assertEquals(iq['type'], 'result')

        cmd = iq.firstChildElement()
        self.assertEquals(cmd.toXml(), self.cmd.toElement().toXml())

    @defer.inlineCallbacks
    def test_PageManager_prev_page_badIndex(self):

        mngr = PageManager()
        mngr.add_page(CommandPage(self.cmd))
        mngr.index = 0
        try:
            yield mngr.prev_page(self.prev_iq, self.state)
        except PageManagerError as e:
            pass

    @defer.inlineCallbacks
    def test_PageManager_prev_page_noPage(self):

        mngr = PageManager()
        mngr.index = 1
        try:
            yield mngr.prev_page(self.prev_iq, self.state)
        except PageManagerError as e:
            pass

    @defer.inlineCallbacks
    def test_PageManager_next_page(self):

        mngr = PageManager()
        mngr.add_page(CommandPage(self.cmd))
        mngr.index = 0
        iq = yield mngr.next_page(self.next_iq, self.state)

        self.assertEquals(mngr.index, 1)

        self.assertEquals(iq['to'], 'requester@master.local')
        self.assertEquals(iq['from'], 'responder@master.local')
        self.assertEquals(iq['id'], 'id1')
        self.assertEquals(iq['type'], 'result')

        cmd = iq.firstChildElement()
        self.assertEquals(cmd.toXml(), self.cmd.toElement().toXml())

    @defer.inlineCallbacks
    def test_PageManager_next_page_start(self):

        mngr = PageManager()
        mngr.add_page(CommandPage(self.cmd))
        mngr.index = 0
        iq = yield mngr.next_page(self.next_start_iq, self.state)

        self.assertEquals(mngr.index, 1)

        self.assertEquals(iq['to'], 'requester@master.local')
        self.assertEquals(iq['from'], 'responder@master.local')
        self.assertEquals(iq['id'], 'id1')
        self.assertEquals(iq['type'], 'result')

        cmd = iq.firstChildElement()
        self.assertEquals(cmd.toXml(), self.cmd.toElement().toXml())

    @defer.inlineCallbacks
    def test_PageManager_next_page_badIndex(self):

        mngr = PageManager()
        mngr.add_page(CommandPage(self.cmd))
        mngr.index = 1
        try:
            yield mngr.next_page(self.next_iq, self.state)
        except PageManagerError as e:
            pass

    @defer.inlineCallbacks
    def test_PageManager_next_page_noPage(self):

        mngr = PageManager()
        mngr.index = 0
        try:
            yield mngr.next_page(self.next_iq, self.state)
        except PageManagerError as e:
            pass

    @defer.inlineCallbacks
    def test_PageManager_ready(self):

        mngr = PageManager()
        mngr.add_page(CommandPage(self.cmd))
        mngr.index = 0
        self.assertFalse(mngr.ready())

        iq = yield mngr.next_page(self.next_start_iq, self.state)

        self.assertTrue(mngr.ready())
        
