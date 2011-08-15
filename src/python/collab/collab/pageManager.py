# Copyright (c) Simon Parry.
# See LICENSE for details.

from twisted.internet import defer
from twisted.words.protocols.jabber import xmlstream
from zope.interface import implements, Interface

from collab.command import getCommand


class PageManagerError(Exception):
    pass

class IPageManager(Interface):

    def reset():
        pass
    
    def add_page(page):
        pass
    
    def cancel_page(iq, s):
        pass

    def prev_page(iq, s):
        pass

    def next_page(iq, s):
        pass
    
    def ready():
        pass

class PageManager(object):
    implements(IPageManager)

    def __init__(self):
        self.index = 0
        self.pages = []

    def reset(self):
        self.index = 0
        
    def add_page(self, page):
        self.pages.append(page)
    
    def cancel_page(self, iq, s):
        self.reset()
        response = xmlstream.toResponse(stanza=iq, stanzaType='result')
        cmd = getCommand(iq)
        cmd.status = 'canceled'
        response.addChild(cmd.toElement())
        return defer.succeed(response)

    def prev_page(self, iq, s):
        if self.index <= 0:
            return defer.fail(PageManagerError('No more pages in history'))
        if len(self.pages) == 0:
            return defer.fail(PageManagerError('No pages loaded'))

        response = xmlstream.toResponse(stanza=iq, stanzaType='result')
        self.index -= 1
        page = self.pages[self.index-1]
        d_el = page.renderToElement(iq, s)
        def cb(el):
            response.addChild(el)
            return response
        
        d_el.addCallback(cb)
        return d_el

    def next_page(self, iq, s):
        if len(self.pages) == 0:
            return defer.fail(PageManagerError('No pages loaded'))
        if self.index == len(self.pages):
            return defer.fail(PageManagerError('No more pages loaded'))

        response = xmlstream.toResponse(stanza=iq, stanzaType='result')
        page = self.pages[self.index]
        d_el = page.renderToElement(iq, s)
        def cb(el):
            response.addChild(el)
            self.index += 1
            return response

        d_el.addCallback(cb)
        return d_el

    def ready(self):
        return self.index == len(self.pages)

