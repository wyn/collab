# Copyright (c) Simon Parry.
# See LICENSE for details.

from twisted.internet import defer
from twisted.python import log
from twisted.words.protocols.jabber import xmlstream, error
from wokkel import data_form
from zope.interface import implements, Interface

import collab
from collab.command import getCommandElement, copyCommandElement, Note


class ICommandHandler(Interface):
    """
    Chain of responsibility pattern
    These do the IQ handling and parsing
    """
    def set_successor(s):
        pass

    def process_iq(iq):
        pass

    def can_process(iq):
        pass

    
class CommandHandler(object):
    implements(ICommandHandler)
    
    def __init__(self, node, stateManager, pageManager):
        self.node = node
        self.stateManager = stateManager
        self.pageManager = pageManager
        self.successor = None
        
    def set_successor(self, s):
        self.successor = s

    def process_iq(self, iq):
        if self.can_process(iq):
            log.msg('Processing with %s on %s' % (self, self.node))
            iq.handled = True
            return self._process(iq)
        
        if self.successor:
            return self.successor.process_iq(iq)

    def can_process(self, iq):
        pass

    def _process(self, iq):

        def reset(e):
            self.pageManager.reset()
            self.stateManager.reset()
            err = xmlstream.toResponse(iq)
            cmd = err.addChild(copyCommandElement(getCommandElement(iq)))
            cmd['status'] = 'complete'
            n = Note(str(e), 'error')
            cmd.addChild(n.toElement())
            return defer.succeed(err)
            
        try:
            s = self._parse_iq(iq)
            s = self._manage_state(s)
        except Exception as e:
            return reset(e)
        else:
            d_response = self._make_next_iq(iq, s)
            def commit(response):
                if not self.pageManager.ready():
                    return defer.succeed(response)

                d_commit = self.stateManager.commit()
                self.pageManager.reset()
                self.stateManager.reset()

                def cb(commit_msg):
                    return response

                def eb(commit_err):
                    e = commit_err.trap(error.StanzaError)
                    if e:
                        cmd = response.firstChildElement()
                        n = Note(str(e), 'error')
                        cmd.addChild(n.toElement())
                        return response

                d_commit.addCallback(cb)
                d_commit.addErrback(eb)
                return d_commit

            d_response.addCallbacks(commit, reset)
            return d_response

    def _parse_iq(self, iq):
        pass

    def _manage_state(self, s):
        pass
    
    def _make_next_iq(self, iq, s):
        pass

class PassThroughHandler(object):
    implements(ICommandHandler)

    def __init__(self):
        self.successor = None
        
    def can_process(self, iq):
        return False

    def set_successor(self, s):
        self.successor = s

    def process_iq(self, iq):
        if self.successor:
            return self.successor.process_iq(iq)


class CancelHandler(CommandHandler):
    
    def __init__(self, node, stateManager, pageManager):
        super(CancelHandler, self).__init__(node, stateManager, pageManager)

    def can_process(self, iq):
        cmd = getCommandElement(iq)
        if not cmd:
            return False

        return cmd.compareAttribute('action', 'cancel') and cmd.compareAttribute('node', self.node)

    def _parse_iq(self, iq):
        return dict()

    def _manage_state(self, s):
        self.stateManager.reset()
        return dict()

    def _make_next_iq(self, iq, s):
        # make cancelled response
        return self.pageManager.cancel_page(iq, s)

class PrevHandler(CommandHandler):
    def __init__(self, node, stateManager, pageManager):
        super(PrevHandler, self).__init__(node, stateManager, pageManager)

    def can_process(self, iq):
        cmd = getCommandElement(iq)
        if not cmd:
            return False

        return cmd.compareAttribute('action', 'prev') and cmd.compareAttribute('node', self.node)

    def _parse_iq(self, iq):
        return self.stateManager.penultimateState()

    def _manage_state(self, s):
        self.stateManager.push(s)
        return self.stateManager.head()

    def _make_next_iq(self, iq, s):
        # send out old cmd with old state
        return self.pageManager.prev_page(iq, s)

class NodeHandler(CommandHandler):
    def __init__(self, node, stateManager, pageManager):
        super(NodeHandler, self).__init__(node, stateManager, pageManager)

    def can_process(self, iq):
        cmd = getCommandElement(iq)
        if not cmd:
            return False

        bs = []
        bs.append(not cmd.compareAttribute('action', 'prev'))
        bs.append(not cmd.compareAttribute('action', 'cancel'))
        bs.append(cmd.hasAttribute('sessionid'))
        bs.append(cmd.compareAttribute('node', self.node))
        return all(bs)

    def _parse_iq(self, iq):
        cmd = getCommandElement(iq)
        form = data_form.findForm(cmd, formNamespace=collab.COLLAB_NS)
        if not form:
            raise ValueError('No Collab forms')

        return form.getValues()

    def _manage_state(self, s):
        self.stateManager.push(s)
        return self.stateManager.head()

    def _make_next_iq(self, iq, s):
        return self.pageManager.next_page(iq, s)

class StartHandler(CommandHandler):
    def __init__(self, node, stateManager, pageManager):
        super(StartHandler, self).__init__(node, stateManager, pageManager)

    def can_process(self, iq):
        cmd = getCommandElement(iq)
        if not cmd:
            return False

        bs = []
        bs.append(not cmd.hasAttribute('sessionid'))
        bs.append(cmd.compareAttribute('node', self.node))
        return all(bs)

    def _parse_iq(self, iq):
        return dict()

    def _manage_state(self, s):
        return dict()

    def _make_next_iq(self, iq, s):
        return self.pageManager.next_page(iq, s)
    
