# Copyright (c) Simon Parry.
# See LICENSE for details.

from datetime import datetime

from twisted.words.xish import xpath
from twisted.words.xish.domish import Element
from wokkel import data_form

import collab


COMMAND_QRY = xpath.XPathQuery(collab.COMMAND_SET)

def hasCommand(iq):
    return COMMAND_QRY.matches(iq)

def getCommandElement(iq):
    if not hasCommand(iq):
        return
    
    cmds = COMMAND_QRY.queryForNodes(iq)
    return cmds[0]

def getCommand(iq):
    if not hasCommand(iq):
        return
    
    return Command.fromElement(getCommandElement(iq))

def copyCommandElement(cmd_el):
    response = Element((collab.COMMAND_NS, 'command'))
    if cmd_el.hasAttribute('sessionid'):
        response['sessionid'] = cmd_el['sessionid']
    if cmd_el.hasAttribute('node'):
        response['node'] = cmd_el['node']
    return response

def copyCommand(cmd):
    c = Command(node=cmd.node, status=cmd.status, sessionid=cmd.sessionid, action=cmd.action)
    c.set_form(cmd.form)
    c.set_actions(cmd.actions)
    [c.addNote(n) for n in cmd.notes]
    return c

class CommandError(Exception):
    pass

class InvalidActionError(CommandError):
    pass

class Actions(object):

    all_actions = set([
        'next', 'prev', 'complete'
        ])
    
    def __init__(self):
        self.actions = set()
        self.default = None

    def add(self, action):
        if action not in self.all_actions:
            raise InvalidActionError('Invalid action added %s' % action)
        self.actions.add(action)

    def remove(self, action):
        if action in self.actions:
            self.actions.remove(action)

    def setDefault(self, default):
        self.add(default)
        self.default = default

    def toElement(self):
        el = Element((None, 'actions'))
        if self.default:
            el['execute'] = self.default

        [el.addElement(a) for a in self.actions]
        return el

    @staticmethod
    def fromElement(element):
        actions = Actions()
        if element.hasAttribute('execute'):
            actions.setDefault(element.getAttribute('execute'))
        for child in element.elements():
            try:
                actions.add(child.name)
            except InvalidActionError as e:
                pass
        return actions

class InvalidNoteTypeError(CommandError):
    pass

class Note(object):
    note_types = ['info', 'warn', 'error']
    
    def __init__(self, content, note_type='info'):
        if note_type not in Note.note_types:
            raise InvalidNoteTypeError('Invalid note type %s' % note_type)
        
        self.content=content
        self.note_type=note_type

    def toElement(self):
        el = Element((None, 'note'))
        el['type'] = self.note_type
        el.addContent(self.content)
        return el

    @staticmethod
    def fromElement(element):
        if not element.hasAttribute('type'):
            raise InvalidNoteTypeError('Cannot create Note without a type')
        t = element.getAttribute('type')
        if t not in Note.note_types:
            t = 'warn'

        content = ''
        if element.children:
            content = element.children[0]

        return Note(content, t)

class InvalidCommandStatusError(CommandError):
    pass

class InvalidCommandActionError(CommandError):
    pass

class InvalidCommandError(CommandError):
    pass

class Command(object):

    allowed_status = ['executing', 'completed', 'canceled']
    allowed_action = ['execute', 'cancel', 'prev', 'next', 'complete']
    
    def __init__(self, node, status=None, sessionid=None, action=None):
        """
        Got to have one of status or action but not both
        action is for incoming, status for replies
        """
        if status and action:
            raise InvalidCommandError('Cannot have a command with both status and action')
        if not status and not action:
            raise InvalidCommandError('Cannot have a command without a status or action')
        
        if status and status not in Command.allowed_status:
            raise InvalidCommandStatusError('Invalid status %s' % status)

        if action and action not in Command.allowed_action:
            raise InvalidCommandActionError('Invalid action %s' % action)
        
        self.node = node
        self.status = status
        self.sessionid = sessionid or '%s:%s' % (node, datetime.isoformat(datetime.now()))
        self.action = action
        self.defaultUri = collab.COMMAND_NS
        self.actions = None
        self.form = None
        self.notes = []

    def addNote(self, note):
        self.notes.append(note)

    def set_actions(self, actions):
        self.actions = actions

    def set_form(self, form):
        self.form = form

    def toElement(self):
        el = Element((self.defaultUri, 'command'))
        el['node'] = self.node
        el['sessionid'] = self.sessionid

        if self.status:
            el['status'] = self.status

        if self.action:
            el['action'] = self.action

        if self.actions:
            el.addChild(self.actions.toElement())

        if self.form:
            el.addChild(self.form.toElement())

        if self.notes:
            [el.addChild(n.toElement()) for n in self.notes]

        return el

    @staticmethod
    def fromElement(element):
        if not element.hasAttribute('node'):
            raise InvalidCommandError('Cannot create Command without a node')
        node = element.getAttribute('node')

        sessionid = None
        if element.hasAttribute('sessionid'):
            sessionid = element.getAttribute('sessionid')

        status = None
        if element.hasAttribute('status'):
            status = element.getAttribute('status')

        action = None
        if element.hasAttribute('action'):
            action = element.getAttribute('action')
            
        c = Command(node, status=status, sessionid=sessionid, action=action)

        for child in element.elements():
            if child.name == 'actions':
                c.set_actions(Actions.fromElement(child))
            elif child.name == 'note':
                c.addNote(Note.fromElement(child))
            elif (child.uri, child.name) == (data_form.NS_X_DATA, 'x'):
                c.set_form(data_form.Form.fromElement(child))

        return c

