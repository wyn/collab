# Copyright (c) Simon Parry.
# See LICENSE for details.

#tests for collabSystemManager module
from twisted.trial import unittest
from twisted.words.protocols.jabber import jid
from wokkel import disco

from collab.xmppMenuSystem import XmppMenuSystem, INFO_FEATURE, ITEMS_FEATURE, COMMAND_FEATURE


testJid = jid.JID('test@master.local')

class XmppMenuSystemTests(unittest.TestCase):

    timeout = 2

    def setUp(self):
        self.xmenu = XmppMenuSystem(
            entity=testJid,
            nodeIdentifier='testTopNode',
            category='testTopCategory',
            idType='testTopType',
            name='testTopName'
            )

    def test_init(self):
        xmenu = XmppMenuSystem(
            entity=testJid,
            nodeIdentifier='testTopNode',
            category='testTopCategory',
            idType='testTopType',
            name='testTopName'
            )
        
        self.assertEquals(xmenu.top, 'testTopNode')

        info, item, parent = xmenu[xmenu.top]

        self.assertEquals(info.nodeIdentifier, 'testTopNode')
        self.assertEquals(info.features, set([INFO_FEATURE, ITEMS_FEATURE]))
        self.assertEquals(info.extensions, {})
        ids = info.identities
        self.assertEquals(len(ids), 1)
        theid = ids[('testTopCategory', 'testTopType')]
        self.assertEquals(theid, 'testTopName')

        self.assertEquals(item.nodeIdentifier, 'testTopNode')
        self.assertEquals(item.entity, testJid)
        self.assertEquals(item.name, 'testTopName')

        self.assertTrue(parent is None)

    def test_addSubMenu(self):
        self.xmenu.addSubMenu(
            entity=testJid,
            nodeIdentifier='testNode',
            parentNodeIdentifier='testTopNode',
            category='testCategory',
            idType='testType',
            name='testName'
            )

        info, item, parent = self.xmenu['testNode']

        self.assertEquals(info.nodeIdentifier, 'testNode')
        self.assertEquals(info.features, set([INFO_FEATURE, ITEMS_FEATURE]))
        self.assertEquals(info.extensions, {})
        ids = info.identities
        self.assertEquals(len(ids), 1)
        theid = ids[('testCategory', 'testType')]
        self.assertEquals(theid, 'testName')

        self.assertEquals(item.nodeIdentifier, 'testNode')
        self.assertEquals(item.entity, testJid)
        self.assertEquals(item.name, 'testName')

        self.assertEquals(parent, 'testTopNode')

    def test_addCommandSubMenu(self):
        self.xmenu.addSubMenu(
            entity=testJid,
            nodeIdentifier='testNode',
            parentNodeIdentifier='testTopNode',
            category='testCategory',
            idType='command-node',
            name='testName'
            )

        info, item, parent = self.xmenu['testNode']

        self.assertEquals(info.nodeIdentifier, 'testNode')
        self.assertEquals(info.features, set([INFO_FEATURE, ITEMS_FEATURE, COMMAND_FEATURE]))
        self.assertEquals(info.extensions, {})
        ids = info.identities
        self.assertEquals(len(ids), 1)
        theid = ids[('testCategory', 'command-node')]
        self.assertEquals(theid, 'testName')

        self.assertEquals(item.nodeIdentifier, 'testNode')
        self.assertEquals(item.entity, testJid)
        self.assertEquals(item.name, 'testName')

        self.assertEquals(parent, 'testTopNode')
        
    def test_addExistingSubMenu(self):
        def add():
            self.xmenu.addSubMenu(
                entity=testJid,
                nodeIdentifier='testNode',
                parentNodeIdentifier='testTopNode',
                category='testCategory',
                idType='testType',
                name='testName'
                )

        add() # add once
        self.assertRaises(KeyError, add)

    def test_addSubMenu_NoParent(self):
        def add():
            self.xmenu.addSubMenu(
                entity=testJid,
                nodeIdentifier='testNode',
                parentNodeIdentifier='nonexistant',
                category='testCategory',
                idType='testType',
                name='testName'
                )

        self.assertRaises(KeyError, add)

    def test_addSubMenuDefaults(self):
        self.xmenu.addSubMenu(
            entity=testJid,
            nodeIdentifier='testNode',
            )

        info, item, parent = self.xmenu['testNode']

        self.assertEquals(info.nodeIdentifier, 'testNode')
        self.assertEquals(info.features, set([INFO_FEATURE, ITEMS_FEATURE]))
        self.assertEquals(info.extensions, {})
        ids = info.identities
        self.assertEquals(len(ids), 1)
        theid = ids[('component', 'generic')]
        self.assertEquals(theid, '')

        self.assertEquals(item.nodeIdentifier, 'testNode')
        self.assertEquals(item.entity, testJid)
        self.assertEquals(item.name, '')

        self.assertEquals(parent, 'testTopNode')


    def test_getChildItems(self):
        self.xmenu.addSubMenu(
            entity=testJid,
            nodeIdentifier='testNode1',
            parentNodeIdentifier='testTopNode'
            )
        self.xmenu.addSubMenu(
            entity=testJid,
            nodeIdentifier='testNode2',
            parentNodeIdentifier='testTopNode'
            )
        self.xmenu.addSubMenu(
            entity=testJid,
            nodeIdentifier='testNode3',
            parentNodeIdentifier='testTopNode'
            )

        items = self.xmenu.getChildItems(parent='testTopNode')
        nodes = []
        for item in items:
            nodes.append(item.nodeIdentifier)
            self.assertEquals(item.entity, testJid)
            self.assertEquals(item.name, '')

        self.assertEquals(len(nodes), 3)
        for i in xrange(3):
            nm = 'testNode%i' % (i+1)
            self.assertTrue(nm in nodes)

    def test_getChildItems_NoParent(self):
        self.xmenu.addSubMenu(
            entity=testJid,
            nodeIdentifier='testNode1',
            parentNodeIdentifier='testTopNode'
            )

        def get():
            self.xmenu.getChildItems(parent='nonexistant')
            
        self.assertRaises(KeyError, get)

    def test_getChildItems_NoItems(self):
        items = self.xmenu.getChildItems(parent='testTopNode')
        expected = disco.DiscoItems()
        self.assertEquals(items.nodeIdentifier, expected.nodeIdentifier)
        self.assertEquals(items._items, expected._items)        
