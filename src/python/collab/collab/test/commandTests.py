# Copyright (c) Simon Parry.
# See LICENSE for details.

#tests for command module
from twisted.trial import unittest
from twisted.words.protocols.jabber import jid
from twisted.words.xish.domish import Element
from wokkel import data_form

import collab
from collab import command
from collab.command import Actions, Note, Command, InvalidActionError, InvalidNoteTypeError, InvalidCommandStatusError, InvalidCommandError, InvalidCommandActionError


testJid = jid.JID('test@master.local')

class ActionTests(unittest.TestCase):

    timeout = 2

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_action(self):
        a = Actions()
        self.assertEquals(a.actions, set())
        self.assertTrue(a.default is None)

    def test_add(self):
        a = Actions()
        a.add('next')
        self.assertEquals(len(a.actions), 1)
        self.assertTrue('next' in a.actions)        

    def test_add_bad(self):
        a = Actions()
        self.assertRaises(InvalidActionError, a.add, 'wrong')

    def test_remove(self):
        a = Actions()
        a.add('prev')
        a.add('next')
        a.remove('prev')
        self.assertEquals(len(a.actions), 1)
        self.assertTrue('next' in a.actions)        

    def test_remove_not_there(self):
        a = Actions()
        a.add('next')
        a.remove('wrong')
        self.assertEquals(len(a.actions), 1)
        self.assertTrue('next' in a.actions)        

    def test_setDefault(self):
        a = Actions()
        a.setDefault('next')
        self.assertEquals(len(a.actions), 1)
        self.assertTrue('next' in a.actions)
        self.assertEquals(a.default, 'next')

    def test_setDefault_bad(self):
        a = Actions()
        self.assertRaises(InvalidActionError, a.setDefault, 'wrong')

    def test_toElement(self):
        a = Actions()
        a.setDefault('next')
        a.add('prev')

        el = Element((None, 'actions'))
        el['execute'] = 'next'
        el.addElement('prev')
        el.addElement('next')

        self.assertEquals(a.toElement().toXml(), el.toXml())
        
    def test_fromElement(self):
        el = Element((None, 'actions'))
        el['execute'] = 'next'
        el.addElement('next')
        el.addElement('prev')

        a = Actions.fromElement(el)
        self.assertEquals(len(a.actions), 2)
        self.assertTrue('next' in a.actions)
        self.assertTrue('prev' in a.actions)
        self.assertEquals(a.default, 'next')

    def test_fromElement_bad(self):
        el = Element((None, 'actions'))
        el['execute'] = 'next'
        el.addElement('next')
        el.addElement('wrong')

        a = Actions.fromElement(el)
        self.assertEquals(len(a.actions), 1)
        self.assertTrue('next' in a.actions)
        self.assertEquals(a.default, 'next')

class NoteTests(unittest.TestCase):

    timeout = 2

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_note(self):
        n = Note('testing the note')
        self.assertEquals(n.note_type, 'info')
        self.assertEquals(n.content, 'testing the note')

    def test_note_note_type(self):
        n = Note('testing the note', note_type='warn')
        self.assertEquals(n.note_type, 'warn')
        self.assertEquals(n.content, 'testing the note')

    def test_note_bad_note_type(self):
        self.assertRaises(InvalidNoteTypeError, Note, 'bla', 'wrong')

    def test_toElement(self):
        n = Note('bla', 'error')

        el = Element((None, 'note'))
        el['type'] = 'error'
        el.addContent('bla')

        self.assertEquals(n.toElement().toXml(), el.toXml())
        
    def test_fromElement(self):
        el = Element((None, 'note'))
        el['type'] = 'error'
        el.addContent('bla')
        n = Note.fromElement(el)

        self.assertEquals(n.note_type, 'error')
        self.assertEquals(n.content, 'bla')

    def test_fromElement_noContent(self):
        el = Element((None, 'note'))
        el['type'] = 'error'
        n = Note.fromElement(el)

        self.assertEquals(n.note_type, 'error')
        self.assertEquals(n.content, '')

    def test_fromElement_bad(self):
        el = Element((None, 'note'))
        el['type'] = 'wrong'
        el.addContent('bla')
        n = Note.fromElement(el)

        self.assertEquals(n.note_type, 'warn')
        self.assertEquals(n.content, 'bla')
        
        
class CommandTest(unittest.TestCase):

    timeout = 2

    def setUp(self):
        def iq():
            iq = Element((None, 'iq'))
            iq['type'] = 'set'
            iq['to'] = 'responder@master.local'
            iq['from'] = 'requester@master.local'
            iq['id'] = 'id1'
            return iq
        self.iq = iq()
        

    def tearDown(self):
        pass

    def test_command(self):
        c = Command('testNode', status='executing')
        self.assertEquals(c.node, 'testNode')
        self.assertEquals(c.defaultUri, collab.COMMAND_NS)
        self.assertEquals(c.status, 'executing')
        self.assertTrue(c.sessionid is not None)
        self.assertEquals(c.notes, [])
        self.assertTrue(c.actions is None)
        self.assertTrue(c.form is None)
        
    def test_command_params(self):
        c = Command('testNode', status='completed', sessionid='sessionid1')
        self.assertEquals(c.node, 'testNode')
        self.assertEquals(c.defaultUri, collab.COMMAND_NS)
        self.assertEquals(c.status, 'completed')
        self.assertEquals(c.sessionid, 'sessionid1')
        self.assertEquals(c.notes, [])
        self.assertTrue(c.actions is None)
        self.assertTrue(c.form is None)
        
    def test_command_params_badstatus(self):
        def create():
            c = Command('testNode', status='wrong', sessionid='sessionid1')

        self.assertRaises(InvalidCommandStatusError, create)

    def test_command_params_badaction(self):
        def create():
            c = Command('testNode', sessionid='sessionid1', action='wrong')

        self.assertRaises(InvalidCommandActionError, create)

    def test_command_params_noActonOrStatus(self):
        def create():
            c = Command('testNode', sessionid='sessionid1')

        self.assertRaises(InvalidCommandError, create)

    def test_command_params_ActionAndStatus(self):
        def create():
            c = Command('testNode', status='completed', sessionid='sessionid1', action='next')

        self.assertRaises(InvalidCommandError, create)

    def test_command_addNote(self):
        c = Command('testNode', status='executing')
        n1 = Note('a test note')
        n2 = Note('another')
        c.addNote(n1)
        c.addNote(n2)

        self.assertEquals(len(c.notes), 2)
        self.assertEquals(c.notes[0], n1)
        self.assertEquals(c.notes[1], n2)        

    def test_command_set_actions(self):
        c = Command('testNode', status='executing')
        a = Actions()
        a.setDefault('next')
        c.set_actions(a)

        self.assertEquals(c.actions, a)

    def test_command_set_form(self):
        c = Command('test', status='executing')
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
            options = [data_form.Option(m) for m in ['one', 'two', 'three']]
            ))

        c.set_form(form)

        self.assertEquals(c.form, form)

    def test_toElement(self):
        c = Command('testNode', status='completed', sessionid='sessionid1')

        n1 = Note('a test note')
        c.addNote(n1)

        a = Actions()
        a.setDefault('next')
        c.set_actions(a)

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
            options = [data_form.Option(m) for m in ['one', 'two', 'three']]
            ))

        c.set_form(form)

        el = Element((collab.COMMAND_NS, 'command'))
        el['node'] = 'testNode'
        el['sessionid'] = 'sessionid1'
        el['status'] = 'completed'
        el.addChild(a.toElement())
        el.addChild(form.toElement())
        el.addChild(n1.toElement())

        self.assertEquals(c.toElement().toXml(), el.toXml())

    def test_fromElement(self):
        el = Element((collab.COMMAND_NS, 'command'))
        el['node'] = 'testNode'
        el['sessionid'] = 'sessionid1'
        el['status'] = 'completed'
        
        a = Actions()
        a.setDefault('next')
        el.addChild(a.toElement())

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
            options = [data_form.Option(m) for m in ['one', 'two', 'three']]
            ))

        el.addChild(form.toElement())

        n1 = Note('a test note')
        el.addChild(n1.toElement())

        c = Command.fromElement(el)

        self.assertEquals(c.node, 'testNode')
        self.assertEquals(c.defaultUri, collab.COMMAND_NS)
        self.assertEquals(c.status, 'completed')
        self.assertEquals(c.sessionid, 'sessionid1')

        self.assertEquals(len(c.notes), 1)
        self.assertEquals(c.notes[0].toElement().toXml(), n1.toElement().toXml())
        self.assertEquals(c.form.toElement().toXml(), form.toElement().toXml())
        self.assertEquals(c.actions.toElement().toXml(), a.toElement().toXml())        

    # module methods
    
    def test_hasCommand(self):
        iq = self.iq
        cmd = Command(node='test', action='execute')
        iq.addChild(cmd.toElement())

        self.assertTrue(command.hasCommand(iq))

    def test_hasNotCommand(self):
        iq = self.iq
        self.assertFalse(command.hasCommand(iq))

    def test_getCommandElement(self):
        iq = self.iq
        cmd = Command(node='test', action='execute')
        iq.addChild(cmd.toElement())

        cmd2 = command.getCommandElement(iq)
        self.assertEquals(cmd2.toXml(), cmd.toElement().toXml())

    def test_getCommandElement(self):
        iq = self.iq
        cmd2 = command.getCommandElement(iq)
        self.assertTrue(cmd2 is None)

    def test_getCommand(self):
        iq = self.iq
        cmd = Command(node='test', action='execute')
        iq.addChild(cmd.toElement())

        cmd2 = command.getCommand(iq)
        self.assertEquals(cmd2.toElement().toXml(), cmd.toElement().toXml())

    def test_getCommand(self):
        iq = self.iq
        cmd2 = command.getCommand(iq)
        self.assertTrue(cmd2 is None)

    def test_copyCommandElement(self):
        cmd = Command(node='test', action='execute')
        cmd_el = cmd.toElement()
        cmd2 = command.copyCommandElement(cmd_el)
        self.assertEquals(cmd2['node'], cmd_el['node'])
        self.assertEquals(cmd2['sessionid'], cmd_el['sessionid'])

    def test_copyCommand(self):
        cmd = Command(node='test', action='execute')
        cmd2 = command.copyCommand(cmd)
        self.assertEquals(cmd2.toElement().toXml(), cmd.toElement().toXml())
