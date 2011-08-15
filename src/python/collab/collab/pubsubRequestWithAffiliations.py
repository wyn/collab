# Copyright (c) Simon Parry.
# See LICENSE for details.

from twisted.words.protocols.jabber import jid
from wokkel import pubsub as ps

import collab


class PubSubRequestComplete(ps.PubSubRequest):
    """
    PubSubRequestComplete: More complete version of the L{ps.PubSubRequest} class
    which includes full treatment of affiliations and subscriptions

    subscriptionForJid and affiliationsForJid are added to handle the case where
    a non-owner asks for its own subscriptions and affiliations

    subscriptionsGet/Set and affiliationsGet/Set handle the case where an owner
    asks for its subscriptions and affiliations for a particular node

    """
    ps.PubSubRequest._requestVerbMap[('get', ps.NS_PUBSUB, 'subscriptions')] = 'subscriptionsForJid'
    ps.PubSubRequest._requestVerbMap[('get', ps.NS_PUBSUB, 'affiliations')] = 'affiliationsForJid'
        
    ps.PubSubRequest._verbRequestMap = dict(((v, k) for k, v in ps.PubSubRequest._requestVerbMap.iteritems()))

    # Map request verb to parameter handler names
    ps.PubSubRequest._parameters['subscriptionsForJid'] = ['subscriptionsForJid']
    ps.PubSubRequest._parameters['affiliationsForJid'] = ['affiliationsForJid']
    ps.PubSubRequest._parameters['affiliationsGet'] = ['nodeOrEmpty', 'affiliations']
    ps.PubSubRequest._parameters['affiliationsSet'] =  ['nodeOrEmpty', 'affiliations']
    ps.PubSubRequest._parameters['subscriptionsGet'] = ['nodeOrEmpty', 'subscriptions']
    ps.PubSubRequest._parameters['subscriptionsSet'] = ['nodeOrEmpty', 'subscriptions']

    affiliationsForJid = None
    subscriptionsForJid = None

    def _parse_affiliationsForJid(self, verbElement):
        self.affiliationsForJid = {}
        for element in verbElement.elements():
            if (element.uri == ps.NS_PUBSUB and
                element.name == 'affiliation'):
                try:
                    node = element['node']
                except KeyError:
                    raise ps.BadRequest(text='Missing node attribute')

                if node in self.affiliationsForJid:
                    raise ps.BadRequest(text='Multiple affiliations for an node')

                try:
                    affiliation = element['affiliation']
                except KeyError:
                    raise ps.BadRequest(text='Missing affiliation attribute')

                self.affiliationsForJid[node] = affiliation

    def _render_affiliationsForJid(self, verbElement):
        if self.affiliationsForJid:
            for node, affiliation in self.affiliationsForJid.items():
                affiliationEl = verbElement.addElement('affiliation')
                affiliationEl['node'] = node
                affiliationEl['affiliation'] = affiliation


    def _render_affiliations(self, verbElement):
        if self.affiliations:
            for jid, affiliation in self.affiliations.items():
                affiliationEl = verbElement.addElement('affiliation')
                affiliationEl['jid'] = jid
                affiliationEl['affiliation'] = affiliation

    def _parse_subscriptions(self, verbElement):
        self.subscriptions = set()
        for element in verbElement.elements():
            if (element.uri == ps.NS_PUBSUB_OWNER and
                element.name == 'subscription'):
                try:
                    subscriber = jid.internJID(element['jid']).userhostJID()
                except KeyError:
                    raise ps.BadRequest(text='Missing jid attribute')

                try:
                    state = element['subscription']
                except KeyError:
                    raise ps.BadRequest(text='Missing subscription attribute')

                try:
                    subid = element['subid']
                except KeyError:
                    subid = None

                sub = ps.Subscription(nodeIdentifier=None, subscriber=subscriber, state=state, subscriptionIdentifier=subid)
                self.subscriptions.add(sub)

    def _parse_subscriptionsForJid(self, verbElement):
        self.subscriptionsForJid = set()
        for element in verbElement.elements():
            if (element.uri == ps.NS_PUBSUB and
                element.name == 'subscription'):
                try:
                    node = element['node']
                except KeyError:
                    raise ps.BadRequest(text='Missing node attribute')

                try:
                    subscriber = jid.internJID(element['jid']).userhostJID()
                except KeyError:
                    raise ps.BadRequest(text='Missing jid attribute')

                try:
                    state = element['subscription']
                except KeyError:
                    raise ps.BadRequest(text='Missing subscription attribute')

                try:
                    subid = element['subid']
                except KeyError:
                    subid = None

                sub = ps.Subscription(nodeIdentifier=node, subscriber=subscriber, state=state, subscriptionIdentifier=subid)
                self.subscriptionsForJid.add(sub)
                
    def _render_subscriptions(self, verbElement):
        if self.subscriptions:
            for sb in self.subscriptions:
                verbElement.addChild(sb.toElement())

    def _render_subscriptionsForJid(self, verbElement):
        if self.subscriptionsForJid:
            for sb in self.subscriptionsForJid:
                verbElement.addChild(sb.toElement())


def makeAffiliations(sender, node, affiliations, xs):
    """
    Utility to make the given node have the given affiliations
    """
    request = PubSubRequestComplete('affiliationsSet')
    request.sender = sender
    request.recipient = jid.JID(collab.PUBSUB_NODE)
    request.nodeIdentifier = node
    request.affiliations = affiliations
    return request.send(xs)

def getAffiliations(sender, node, xs):
    """
    Utility for getting affiliations of a pubsub node
    as requested by the owner of the pubsub node
    e.g. hamlet below
    <iq type='get'
        from='hamlet@denmark.lit/elsinore'
        to='pubsub.shakespeare.lit'
        id='ent1'>
      <pubsub xmlns='http://jabber.org/protocol/pubsub#owner'>
        <affiliations node='princely_musings'/>
      </pubsub>
    </iq>
    """
    request = PubSubRequestComplete('affiliationsGet')
    request.sender = sender
    request.recipient = jid.JID(collab.PUBSUB_NODE)
    request.nodeIdentifier = node
    d = request.send(xs)
    def parse(element):
        element['type'] = 'get' # have to do this to make the parsing kick in?
        request.parseElement(element)
        return request.affiliations

    d.addCallback(parse)
    return d

def getAffiliationsForJid(sender, xs):
    """
    Utility for getting affiliations of a JID that is not necessarily the owner
    e.g. sending this request when francisco is not nec an owner:
    <iq type='get'
        from='francisco@denmark.lit/barracks'
        to='pubsub.shakespeare.lit'
        id='affil1'>
      <pubsub xmlns='http://jabber.org/protocol/pubsub'>
        <affiliations/>
      </pubsub>
    </iq>

    """
    request = PubSubRequestComplete('affiliationsForJid')
    request.sender = sender
    request.recipient = jid.JID(collab.PUBSUB_NODE)
    d = request.send(xs)
    def parse(element):
        element['type'] = 'get' # have to do this to make the parsing kick in?
        request.parseElement(element)
        return request.affiliationsForJid

    d.addCallback(parse)
    return d

def makeSubscriptions(sender, node, subscriptions, xs):
    """
    Utility to make subscriptions, sender has to be the node owner
    e.g. hamlet is the owner
    <iq type='get'
        from='hamlet@denmark.lit/elsinore'
        to='pubsub.shakespeare.lit'
        id='subman1'>
      <pubsub xmlns='http://jabber.org/protocol/pubsub#owner'>
        <subscriptions node='princely_musings'/>
      </pubsub>
    </iq>

    """
    request = PubSubRequestComplete('subscriptionsSet')
    request.sender = sender
    request.recipient = jid.JID(collab.PUBSUB_NODE)
    request.nodeIdentifier = node
    request.subscriptions = subscriptions
    return request.send(xs)

def getSubscriptions(sender, node, xs):
    """
    Utility for getting subscriptions of a pubsub node from the owner
    e.g.
    <iq type='get'
        from='hamlet@denmark.lit/elsinore'
        to='pubsub.shakespeare.lit'
        id='subman1'>
      <pubsub xmlns='http://jabber.org/protocol/pubsub#owner'>
        <subscriptions node='princely_musings'/>
      </pubsub>
    </iq>
    """
    request = PubSubRequestComplete('subscriptionsGet')
    request.sender = sender
    request.recipient = jid.JID(collab.PUBSUB_NODE)
    request.nodeIdentifier = node
    d = request.send(xs)
    def parse(element):
        element['type'] = 'get' # have to do this to make the parsing kick in?
        request.parseElement(element)
        return request.subscriptions

    d.addCallback(parse)
    return d

def getSubscriptionsForJid(sender, xs):
    """
    Utility for getting subscriptions of a JID that is not necessarily the owner
    e.g.
    <iq type='get'
        from='francisco@denmark.lit/barracks'
        to='pubsub.shakespeare.lit'
        id='subscriptions1'>
      <pubsub xmlns='http://jabber.org/protocol/pubsub'>
        <subscriptions/>
      </pubsub>
    </iq>
    
    """
    request = PubSubRequestComplete('subscriptionsForJid')
    request.sender = sender
    request.recipient = jid.JID(collab.PUBSUB_NODE)
    d = request.send(xs)
    def parse(element):
        element['type'] = 'get' # have to do this to make the parsing kick in?
        request.parseElement(element)
        return request.subscriptionsForJid

    d.addCallback(parse)
    return d
