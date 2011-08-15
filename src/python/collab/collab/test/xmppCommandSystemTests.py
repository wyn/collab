# Copyright (c) Simon Parry.
# See LICENSE for details.

#tests for stateManager module
from mock import Mock
from twisted.internet import defer
from twisted.python import failure
from twisted.trial import unittest
from twisted.words.protocols.jabber import jid, error, xmlstream
from twisted.words.xish.domish import Element
from wokkel import data_form

import collab
from collab.command import Command, Note, copyCommandElement, getCommandElement
from collab.pageManager import PageManagerError
from collab.stateManager import EmptyStateManagerError
from collab.test import utils
from collab.xmppCommandSystem import CommandHandler, CancelHandler, PrevHandler, NodeHandler, PassThroughHandler, StartHandler


testJid = jid.JID('test@master.local')

def iq():
    iq = Element((None, 'iq'))
    iq['type'] = 'set'
    iq['to'] = 'responder@master.local'
    iq['from'] = 'requester@master.local'
    iq['id'] = 'id1'
    return iq

def cmd():
    c = Command(node='test', action='execute')
    return c.toElement()

def makeErr(e, iq):
    err = xmlstream.toResponse(iq)
    cmd = err.addChild(copyCommandElement(getCommandElement(iq)))
    cmd['status'] = 'complete'
    n = Note(e, 'error')
    cmd.addChild(n.toElement())
    return err

class CommandHandlerTests(unittest.TestCase):

    timeout = 2

    def setUp(self):
        self.stateMngr = Mock()
        self.pageMngr = Mock()
        self.chdlr = CommandHandler('testNode1', self.stateMngr, self.pageMngr)
        self.next_hdlr = CommandHandler('testNode2', self.stateMngr, self.pageMngr)
        self.chdlr.successor = self.next_hdlr
        self.iq = iq()
        self.iq.addChild(cmd())

    def tearDown(self):
        pass

    def test_process_iq(self):
        self.next_hdlr.process_iq = Mock()
        self.chdlr.can_process = Mock(return_value = True)
        self.chdlr._process = Mock(side_effect=utils.good_side_effect('hello'))

        iq = self.iq
        d = self.chdlr.process_iq(iq)

        self.chdlr.can_process.assertCalledOnceWith(iq)
        self.chdlr._process.assertCalledOnceWith(iq)        
        self.assertFalse(self.next_hdlr.process_iq.called)

        def check(val):
            self.assertEquals(val, 'hello')

        d.addCallback(check)
        return d

    def test_process_iq_cantprocess(self):
        self.next_hdlr.process_iq = Mock(side_effect=utils.good_side_effect('hello'))
        self.chdlr.can_process = Mock(return_value = False)
        self.chdlr._process = Mock()

        iq = self.iq
        d = self.chdlr.process_iq(iq)

        self.assertTrue(self.chdlr.can_process.called)
        self.assertFalse(self.chdlr._process.called)
        self.assertTrue(self.next_hdlr.process_iq.called)

        def check(val):
            self.assertEquals(val, 'hello')

        d.addCallback(check)
        return d

    def test_process_iq_nosuccessor(self):
        self.successor = None
        self.chdlr.can_process = Mock(return_value = False)
        self.chdlr._process = Mock()

        iq = self.iq
        d = self.chdlr.process_iq(iq)

        self.assertTrue(self.chdlr.can_process.called)
        self.assertFalse(self.chdlr._process.called)
        self.assertTrue(d is None)

    def test__process(self):
        s = dict()
        self.chdlr._parse_iq = Mock(return_value=s)
        self.chdlr._manage_state = Mock(return_value=s)

        iq = self.iq
        response = xmlstream.toResponse(iq)
        self.chdlr._make_next_iq = Mock(side_effect=utils.good_side_effect(response))

        self.pageMngr.ready = Mock(return_value=True)
        self.stateMngr.commit = Mock(side_effect=utils.good_side_effect('Committed stuff'))

        self.pageMngr.reset = Mock()
        self.stateMngr.reset = Mock()

        d = self.chdlr._process(iq)
        
        def cb(msg):
            self.chdlr._parse_iq.assert_called_once_with(iq)
            self.chdlr._manage_state.assert_called_once_with(s)
            self.chdlr._make_next_iq.assert_called_once_with(iq, s)
            self.assertEquals(msg, response)

        d.addCallback(cb)
        return d

    def test__process_parseThrows(self):
        self.chdlr._parse_iq = Mock(side_effect=ValueError('%s: No Collab forms' % self.__class__))
        self.chdlr._manage_state = Mock()
        self.chdlr._make_next_iq = Mock()

        iq = self.iq
        d = self.chdlr._process(iq)
        
        self.assertTrue(self.chdlr._parse_iq.called)
        self.assertFalse(self.chdlr._manage_state.called)
        self.assertFalse(self.chdlr._make_next_iq.called)

        def cb(msg):
            err = makeErr('%s: No Collab forms' % self.__class__, iq)
            self.assertEquals(msg.toXml(), err.toXml())

        d.addCallback(cb)
        return d

    def test__process_manageStateThrows(self):
        self.chdlr._parse_iq = Mock()
        self.chdlr._manage_state = Mock(side_effect=EmptyStateManagerError('%s: Cannot revert to previous state' % self.__class__))
        self.chdlr._make_next_iq = Mock()

        iq = self.iq
        d = self.chdlr._process(iq)
        
        self.assertTrue(self.chdlr._parse_iq.called)
        self.assertTrue(self.chdlr._manage_state.called)
        self.assertFalse(self.chdlr._make_next_iq.called)

        def cb(msg):
            err = makeErr('%s: Cannot revert to previous state' % self.__class__, iq)
            self.assertEquals(msg.toXml(), err.toXml())

        d.addCallback(cb)
        return d

    def test__process_makeNextIqThrows(self):
        self.chdlr._parse_iq = Mock()
        self.chdlr._manage_state = Mock()
        self.chdlr._make_next_iq = Mock(side_effect=utils.bad_side_effect(PageManagerError('%s: Massive corn clog in port seven' % self.__class__)))

        iq = self.iq
        d = self.chdlr._process(iq)
        
        self.assertTrue(self.chdlr._parse_iq.called)
        self.assertTrue(self.chdlr._manage_state.called)
        self.assertTrue(self.chdlr._make_next_iq.called)

        def cb(msg):
            f = failure.Failure('%s: Massive corn clog in port seven' % self.__class__, PageManagerError)
            err = makeErr(str(f), iq)
            self.assertEquals(msg.toXml(), err.toXml())

        d.addCallback(cb)
        return d

    def test__process_readyToCommitOK(self):
        self.chdlr._parse_iq = Mock()
        self.chdlr._manage_state = Mock()
        
        response = xmlstream.toResponse(self.iq)
        self.chdlr._make_next_iq = Mock(side_effect=utils.good_side_effect(response))

        self.pageMngr.ready = Mock(return_value=True)
        self.stateMngr.commit = Mock(side_effect=utils.good_side_effect('Committed stuff'))

        self.pageMngr.reset = Mock()
        self.stateMngr.reset = Mock()

        def checkIt(msg):
            self.assertTrue(self.pageMngr.ready.called)
            self.assertTrue(self.stateMngr.commit.called)
            self.assertTrue(self.pageMngr.reset.called)
            self.assertTrue(self.stateMngr.reset.called)
            self.assertEquals(msg, response)

        d = self.chdlr._process(self.iq)
        d.addCallback(checkIt)
        return d

    def test__process_readyToCommitNotOK_stanzaError(self):
        self.chdlr._parse_iq = Mock()
        self.chdlr._manage_state = Mock()
        
        response = xmlstream.toResponse(iq())
        response.addChild(cmd())
        self.chdlr._make_next_iq = Mock(side_effect=utils.good_side_effect(response))

        self.pageMngr.ready = Mock(return_value=True)
        self.stateMngr.commit = Mock(side_effect=utils.bad_side_effect(error.StanzaError('%s: Committed fail' % self.__class__)))

        self.pageMngr.reset = Mock()
        self.stateMngr.reset = Mock()

        def checkIt(msg):
            self.assertTrue(self.pageMngr.ready.called)
            self.assertTrue(self.stateMngr.commit.called)
            self.assertTrue(self.pageMngr.reset.called)
            self.assertTrue(self.stateMngr.reset.called)
            self.assertEquals(msg, response)
            self.assertTrue(msg.firstChildElement().firstChildElement().name, 'note')

        d = self.chdlr._process(self.iq)
        d.addCallback(checkIt)
        return d

    def test__process_readyToCommitNotOK_otherError(self):
        self.chdlr._parse_iq = Mock()
        self.chdlr._manage_state = Mock()
        
        response = xmlstream.toResponse(iq())
        response.addChild(cmd())
        self.chdlr._make_next_iq = Mock(side_effect=utils.good_side_effect(response))

        self.pageMngr.ready = Mock(return_value=True)
        self.stateMngr.commit = Mock(side_effect=utils.bad_side_effect(ValueError('%s: Committed fail' % self.__class__)))

        self.pageMngr.reset = Mock()
        self.stateMngr.reset = Mock()

        def checkIt(msg):
            self.assertTrue(self.pageMngr.ready.called)
            self.assertTrue(self.stateMngr.commit.called)
            self.assertTrue(self.pageMngr.reset.called)
            self.assertTrue(self.stateMngr.reset.called)
            self.assertNotEquals(msg, response)

        d = self.chdlr._process(self.iq)
        d.addCallbacks(lambda _: self.assertTrue(False), checkIt)
        return d


class PassThroughHandlerTests(unittest.TestCase):
    """
    PassThroughHandlerTests: Simple tests for the pass through handler
    
    """
    
    timeout = 2
    
    def setUp(self):
    	pass
    
    def tearDown(self):
    	pass

    def test_can_process(self):
        pt = PassThroughHandler()
        self.assertFalse(pt.can_process(iq()))

    
class CancelHandlerTests(unittest.TestCase):

    timeout = 2

    def setUp(self):
        self.stateMngr = Mock()
        self.pageMngr = Mock()
        self.iq = iq()
        
    def tearDown(self):
        pass

    def test_can_process_nocmd(self):
        cancel = CancelHandler('nodeTest', self.stateMngr, self.pageMngr)
        self.assertFalse(cancel.can_process(self.iq))

    def test_can_process_notCancel(self):
        cancel = CancelHandler('nodeTest', self.stateMngr, self.pageMngr)
        iq = self.iq
        cmd = Command(node='nodeTest', action='next')
        iq.addChild(cmd.toElement())
        self.assertFalse(cancel.can_process(iq))

    def test_can_process_wrongNode(self):
        cancel = CancelHandler('nodeTest', self.stateMngr, self.pageMngr)
        iq = self.iq
        cmd = Command(node='wrongNode', action='cancel')
        iq.addChild(cmd.toElement())
        self.assertFalse(cancel.can_process(iq))

    def test_can_process(self):
        cancel = CancelHandler('nodeTest', self.stateMngr, self.pageMngr)
        iq = self.iq
        cmd = Command(node='nodeTest', action='cancel')
        iq.addChild(cmd.toElement())
        self.assertTrue(cancel.can_process(iq))

    def test_parse_iq(self):
        cancel = CancelHandler('nodeTest', self.stateMngr, self.pageMngr)
        self.assertEquals(cancel._parse_iq(self.iq), dict())
        
    def test_manage_state(self):
        self.stateMngr.reset = Mock()
        cancel = CancelHandler('nodeTest', self.stateMngr, self.pageMngr)
        s = cancel._manage_state(None)

        self.assertTrue(self.stateMngr.reset.called)
        self.assertEquals(s, dict())

    def test_make_next_iq(self):
        self.pageMngr.cancel_page = Mock(return_value=defer.succeed(iq()))
        cancel = CancelHandler('nodeTest', self.stateMngr, self.pageMngr)
        iq1 = self.iq
        s = dict()
        d_iq2 = cancel._make_next_iq(iq1, s)

        def checkIt(iq2):
            self.pageMngr.cancel_page.assert_called_once_with(iq1, s)
            self.assertEquals(iq2.toXml(), iq().toXml())

        d_iq2.addCallback(checkIt)
        return d_iq2
                        
class PrevHandlerTests(unittest.TestCase):

    timeout = 2

    def setUp(self):
        self.stateMngr = Mock()
        self.pageMngr = Mock()
        self.iq = iq()

    def tearDown(self):
        pass

    def test_can_process_nocmd(self):
        prev = PrevHandler('nodeTest', self.stateMngr, self.pageMngr)
        self.assertFalse(prev.can_process(self.iq))

    def test_can_process_notPrev(self):
        prev = PrevHandler('nodeTest', self.stateMngr, self.pageMngr)
        iq = self.iq
        cmd = Command(node='nodeTest', action='next')
        iq.addChild(cmd.toElement())
        self.assertFalse(prev.can_process(iq))

    def test_can_process_wrongNode(self):
        prev = PrevHandler('nodeTest', self.stateMngr, self.pageMngr)
        iq = self.iq
        cmd = Command(node='wrongNode', action='prev')
        iq.addChild(cmd.toElement())
        self.assertFalse(prev.can_process(iq))

    def test_can_process(self):
        prev = PrevHandler('nodeTest', self.stateMngr, self.pageMngr)
        iq = self.iq
        cmd = Command(node='nodeTest', action='prev')
        iq.addChild(cmd.toElement())
        self.assertTrue(prev.can_process(iq))

    def test_parse_iq(self):
        dct1 = dict({'one': 1})
        self.stateMngr.penultimateState = Mock(return_value=dct1)
        prev = PrevHandler('nodeTest', self.stateMngr, self.pageMngr)
        dct2 = prev._parse_iq(self.iq)

        self.assertTrue(self.stateMngr.penultimateState.called)
        self.assertEquals(dct2, dct1)

    def test_manage_state(self):
        self.stateMngr.push = Mock()
        s1 = dict()
        self.stateMngr.head = Mock(return_value=s1)
        prev = PrevHandler('nodeTest', self.stateMngr, self.pageMngr)
        s2 = dict()
        s3 = prev._manage_state(s2)

        self.stateMngr.push.assert_called_once_with(s2)
        self.assertEquals(s3, s1)

    def test_make_next_iq(self):
        self.pageMngr.prev_page = Mock(side_effect=utils.good_side_effect(iq()))
        prev = PrevHandler('nodeTest', self.stateMngr, self.pageMngr)
        iq1 = self.iq
        d_iq2 = prev._make_next_iq(iq1, None)

        def checkIt(iq2):
            self.assertTrue(self.pageMngr.prev_page.called)
            self.assertEquals(iq2.toXml(), iq().toXml())

        d_iq2.addCallback(checkIt)
        return d_iq2
        
    
class NodeHandlerTests(unittest.TestCase):

    timeout = 2

    def setUp(self):
        self.stateMngr = Mock()
        self.pageMngr = Mock()
        self.iq = iq()
        
    def tearDown(self):
        pass

    def test_can_process_nocmd(self):
        node = NodeHandler('nodeTest', self.stateMngr, self.pageMngr)
        self.assertFalse(node.can_process(self.iq))

    def test_can_process_notActionPrev(self):
        node = NodeHandler('nodeTest', self.stateMngr, self.pageMngr)
        iq = self.iq
        cmd = Command(node='nodeTest', action='prev')
        iq.addChild(cmd.toElement())
        self.assertFalse(node.can_process(iq))

    def test_can_process_notActionCancel(self):
        node = NodeHandler('nodeTest', self.stateMngr, self.pageMngr)
        iq = self.iq
        cmd = Command(node='nodeTest', action='cancel')
        iq.addChild(cmd.toElement())
        self.assertFalse(node.can_process(iq))

    def test_can_process_wrongNode(self):
        node = NodeHandler('nodeTest', self.stateMngr, self.pageMngr)
        iq = self.iq
        cmd = Command(node='wrongNode', action='cancel')
        iq.addChild(cmd.toElement())
        self.assertFalse(node.can_process(iq))

    def test_can_process(self):
        node = NodeHandler('nodeTest', self.stateMngr, self.pageMngr)
        iq = self.iq
        cmd = Command(node='nodeTest', action='next')
        iq.addChild(cmd.toElement())
        self.assertTrue(node.can_process(iq))

    def test_parse_iq(self):
        node = NodeHandler('nodeTest', self.stateMngr, self.pageMngr)
        iq = self.iq
        cmd = Command(node='nodeTest', action='next')
        form = data_form.Form(
            formType='submit',
            formNamespace=collab.COLLAB_NS
            )

        form.addField(data_form.Field(
            var = 'machine',
            value = 'one'
            ))

        cmd.set_form(form)
        iq.addChild(cmd.toElement())

        vals = node._parse_iq(iq)
        self.assertEquals(vals['machine'], 'one')

    def test_parse_iq_badForm(self):
        node = NodeHandler('nodeTest', self.stateMngr, self.pageMngr)
        iq = self.iq
        cmd = Command(node='nodeTest', action='next')
        form = data_form.Form(
            formType='submit',
            formNamespace='wrong'
            )

        form.addField(data_form.Field(
            var = 'machine',
            value = 'one'
            ))

        form.getValues = Mock(return_value=dict({'machine': 'one'}))
        cmd.set_form(form)
        iq.addChild(cmd.toElement())

        def raises():
            return node._parse_iq(iq)

        self.assertRaises(ValueError, raises)
        self.assertFalse(form.getValues.called)

    def test_manage_state(self):
        self.stateMngr.push = Mock()
        s1 = dict()
        self.stateMngr.head = Mock(return_value=s1)
        node = NodeHandler('nodeTest', self.stateMngr, self.pageMngr)
        s2 = dict()
        s3 = node._manage_state(s2)

        self.stateMngr.push.assert_called_once_with(s2)
        self.assertEquals(s3, s1)

    def test_make_next_iq(self):
        self.pageMngr.next_page = Mock(side_effect=utils.good_side_effect(iq()))
        node = NodeHandler('nodeTest', self.stateMngr, self.pageMngr)
        iq1 = self.iq
        d_iq2 = node._make_next_iq(iq1, None)

        def checkIt(iq2):
            self.assertTrue(self.pageMngr.next_page.called)
            self.assertEquals(iq2.toXml(), iq().toXml())

        d_iq2.addCallback(checkIt)
        return d_iq2
                        
        
class StartHandlerTests(unittest.TestCase):
    """
    StartHandlerTests: Simple tests for the L{StartHandler}
    
    """
    
    timeout = 2
    
    def setUp(self):
        self.stateMngr = Mock()
        self.pageMngr = Mock()
        self.iq = iq()
        
    def tearDown(self):
        pass

    def test_can_process_nocmd(self):
        node = StartHandler('nodeTest', self.stateMngr, self.pageMngr)
        self.assertFalse(node.can_process(self.iq))

    def test_can_process_hasSessionId(self):
        node = StartHandler('nodeTest', self.stateMngr, self.pageMngr)
        iq = self.iq
        cmd = Command(node='nodeTest', action='prev')
        iq.addChild(cmd.toElement())
        self.assertFalse(node.can_process(iq))

    def test_can_process_wrongNode(self):
        node = StartHandler('nodeTest', self.stateMngr, self.pageMngr)
        iq = self.iq
        cmd = Command(node='wrongNode', action='cancel')
        iq.addChild(cmd.toElement())
        self.assertFalse(node.can_process(iq))

    def test_can_process(self):
        node = StartHandler('nodeTest', self.stateMngr, self.pageMngr)
        iq = self.iq
        cmd = Command(node='nodeTest', action='next')
        cmd_el = cmd.toElement()
        del cmd_el['sessionid']
        iq.addChild(cmd_el)
        self.assertTrue(node.can_process(iq))

    def test_parse_iq(self):
        node = StartHandler('nodeTest', self.stateMngr, self.pageMngr)
        s = node._parse_iq(self.iq)
        self.assertEquals(s, dict())
        
    def test_manage_state(self):
        node = StartHandler('nodeTest', self.stateMngr, self.pageMngr)
        s = node._manage_state(None)
        self.assertEquals(s, dict())
        
    def test_make_next_iq(self):
        self.pageMngr.next_page = Mock(side_effect=utils.good_side_effect(iq()))
        node = StartHandler('nodeTest', self.stateMngr, self.pageMngr)
        iq1 = self.iq
        d_iq2 = node._make_next_iq(iq1, None)

        def checkIt(iq2):
            self.assertTrue(self.pageMngr.next_page.called)
            self.assertEquals(iq2.toXml(), iq().toXml())

        d_iq2.addCallback(checkIt)
        return d_iq2
