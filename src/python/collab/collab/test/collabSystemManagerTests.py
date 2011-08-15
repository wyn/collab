# Copyright (c) Simon Parry.
# See LICENSE for details.

#tests for collabSystemManager module
from mock import Mock, MagicMock
from twisted.trial import unittest
from twisted.words.protocols.jabber import jid

from collab.collabSystemManager import CollabSystemManager


class CollabSystemManagerTests(unittest.TestCase):

    timeout = 2
    testJid = jid.JID('test@master.local')

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_getDiscoInfo_badTarget(self):
        csm = CollabSystemManager(self.testJid)
        info = csm.getDiscoInfo(jid.JID('notused@master.local'), jid.JID('bad@master.local'))
        self.assertTrue(info is None)
        
    def test_getDiscoInfo_noNodeID(self):
        csm = CollabSystemManager(self.testJid)
        csm.menu = MagicMock()
        csm.menu.top = 'top'
        csm.menu.__getitem__.return_value = 'top info', None, None
        info = csm.getDiscoInfo(jid.JID('notused@master.local'), self.testJid)

        csm.menu.__getitem__.assert_called_with('top')
        self.assertEquals(info, 'top info')

    def test_getDiscoInfo_withNodeID(self):
        csm = CollabSystemManager(self.testJid)
        csm.menu = MagicMock()
        csm.menu.__getitem__.return_value = 'node info', None, None
        info = csm.getDiscoInfo(jid.JID('notused@master.local'), self.testJid, 'the node')

        csm.menu.__getitem__.assert_called_with('the node')
        self.assertEquals(info, 'node info')

    def test_getDiscoInfo_withUnknownNodeID(self):
        csm = CollabSystemManager(self.testJid)
        csm.menu = MagicMock()
        csm.menu.__getitem__.side_effect = KeyError
        info = csm.getDiscoInfo(jid.JID('notused@master.local'), self.testJid, 'unknown node')

        csm.menu.__getitem__.assert_called_with('unknown node')
        self.assertTrue(info is None)

    def test_getDiscoItems_badTarget(self):
        csm = CollabSystemManager(self.testJid)
        items = csm.getDiscoItems(jid.JID('notused@master.local'), jid.JID('bad@master.local'))
        self.assertEquals(items, [])
        
    def test_getDiscoItems_noNodeID(self):
        csm = CollabSystemManager(self.testJid)
        items = ['item1', 'item2']
        csm.menu.getChildItems = Mock(return_value=items)
        actual = csm.getDiscoItems(jid.JID('notused@master.local'), self.testJid)

        self.assertEquals(actual, items)
        csm.menu.getChildItems.assert_called_with(csm.menu.top)
        
    def test_getDiscoItems_withNodeID(self):
        csm = CollabSystemManager(self.testJid)
        items = ['item1', 'item2']
        csm.menu.getChildItems = Mock(return_value=items)
        actual = csm.getDiscoItems(jid.JID('notused@master.local'), self.testJid, 'the node')

        self.assertEquals(actual, items)
        csm.menu.getChildItems.assert_called_with('the node')

    def test_getDiscoItems_badNodeID(self):
        csm = CollabSystemManager(self.testJid)
        csm.menu.getChildItems = Mock(side_effect=KeyError)
        actual = csm.getDiscoItems(jid.JID('notused@master.local'), self.testJid, 'the node')

        self.assertEquals(actual, [])
        csm.menu.getChildItems.assert_called_with('the node')
        

        
        
