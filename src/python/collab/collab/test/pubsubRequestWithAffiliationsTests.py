# Copyright (c) Simon Parry.
# See LICENSE for details.

from mock import Mock, patch
from twisted.trial import unittest
from twisted.words.protocols.jabber import jid
from wokkel import pubsub as ps
from wokkel.generic import parseXml

from collab import pubsubRequestWithAffiliations as psaff
from collab.test import utils


class PubSubRequestCompleteTests(unittest.TestCase):
    """
    PubSubRequestCompleteTests: Tests for the PubSubRequestComplete class
    
    """
    
    timeout = 2
    
    def setUp(self):
    	pass
    
    def tearDown(self):
    	pass

    @patch('collab.pubsubRequestWithAffiliations.PubSubRequestComplete.send')
    def test_getAffiliations_current(self, sendMock):
        xml = """
        <iq type='result'
            from='pubsub.shakespeare.lit'
            to='hamlet@denmark.lit/elsinore'
            id='ent1'>
          <pubsub xmlns='http://jabber.org/protocol/pubsub#owner'>
            <affiliations node='princely_musings'>
              <affiliation jid='hamlet@denmark.lit' affiliation='owner'/>
              <affiliation jid='polonius@denmark.lit' affiliation='outcast'/>
            </affiliations>
          </pubsub>
        </iq>
        """
        el = parseXml(xml)
        sendMock.side_effect = utils.good_side_effect(el)
        xs = Mock()
        d = psaff.getAffiliations(jid.JID('hamlet@denmark.lit/elsinore'), 'princely_musings', xs)

        def cb(affs):
            expected = {
                jid.internJID('hamlet@denmark.lit').userhostJID(): 'owner',
                jid.internJID('polonius@denmark.lit').userhostJID(): 'outcast',
                }
            self.assertEquals(expected, affs)
            sendMock.assert_called_once_with(xs)

        d.addCallback(cb)
        return d
        
    @patch('collab.pubsubRequestWithAffiliations.PubSubRequestComplete.send')
    def test_getAffiliations_notSupported(self, sendMock):
        xml = """
        <iq type='error'
            from='pubsub.shakespeare.lit'
            id='ent1'>
          <error type='cancel'>
            <feature-not-implemented xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/>
            <unsupported xmlns='http://jabber.org/protocol/pubsub#errors'
                         feature='modify-affiliations'/>
          </error>
        </iq>
        """
        el = parseXml(xml)
        sendMock.side_effect = utils.good_side_effect(el)
        xs = Mock()
        d = psaff.getAffiliationsForJid(jid.JID('francisco@denmark.lit'), xs)

        # wokkel doesn't account for this situation yet
        return self.assertFailure(d, AttributeError)
        
    @patch('collab.pubsubRequestWithAffiliations.PubSubRequestComplete.send')
    def test_getAffiliations_notOwner(self, sendMock):
        xml = """
        <iq type='error'
            from='pubsub.shakespeare.lit'
            id='ent1'>
          <error type='auth'>
            <forbidden xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/>
          </error>
        </iq>
        """
        el = parseXml(xml)
        sendMock.side_effect = utils.good_side_effect(el)
        xs = Mock()
        d = psaff.getAffiliationsForJid(jid.JID('francisco@denmark.lit'), xs)

        # wokkel doesn't account for this situation yet
        return self.assertFailure(d, AttributeError)
        
    @patch('collab.pubsubRequestWithAffiliations.PubSubRequestComplete.send')
    def test_getAffiliations_notExist(self, sendMock):
        xml = """
        <iq type='error'
            from='pubsub.shakespeare.lit'
            id='ent1'>
          <error type='cancel'>
            <item-not-found xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/>
          </error>
        </iq>
        """
        el = parseXml(xml)
        sendMock.side_effect = utils.good_side_effect(el)
        xs = Mock()
        d = psaff.getAffiliationsForJid(jid.JID('francisco@denmark.lit'), xs)

        # wokkel doesn't account for this situation yet
        return self.assertFailure(d, AttributeError)
        
    @patch('collab.pubsubRequestWithAffiliations.PubSubRequestComplete.send')
    def test_getAffiliationsForJid_current(self, sendMock):
        xml = """
        <iq type='result'
            from='pubsub.shakespeare.lit'
            to='francisco@denmark.lit'
            id='affil1'>
          <pubsub xmlns='http://jabber.org/protocol/pubsub'>
            <affiliations>
              <affiliation node='node1' affiliation='owner'/>
              <affiliation node='node2' affiliation='publisher'/>
              <affiliation node='node5' affiliation='outcast'/>
              <affiliation node='node6' affiliation='owner'/>
            </affiliations>
          </pubsub>
        </iq>
        """
        el = parseXml(xml)
        sendMock.side_effect = utils.good_side_effect(el)
        xs = Mock()
        d = psaff.getAffiliationsForJid(jid.JID('francisco@denmark.lit'), xs)

        def cb(affs):
            expected = {
                'node1': 'owner',
                'node2': 'publisher',
                'node5': 'outcast',
                'node6': 'owner'
                }
            self.assertEquals(expected, affs)
            sendMock.assert_called_once_with(xs)

        d.addCallback(cb)
        return d
        
    @patch('collab.pubsubRequestWithAffiliations.PubSubRequestComplete.send')
    def test_getAffiliationsForJid_none(self, sendMock):
        xml = """
        <iq type='result'
            from='pubsub.shakespeare.lit'
            to='francisco@denmark.lit/barracks'
            id='affil1'>
          <pubsub xmlns='http://jabber.org/protocol/pubsub'>
            <affiliations/>
          </pubsub>
        </iq>
        """
        el = parseXml(xml)
        sendMock.side_effect = utils.good_side_effect(el)
        xs = Mock()
        d = psaff.getAffiliationsForJid(jid.JID('francisco@denmark.lit'), xs)

        def cb(affs):
            expected = {}
            self.assertEquals(expected, affs)
            sendMock.assert_called_once_with(xs)

        d.addCallback(cb)
        return d
        
    @patch('collab.pubsubRequestWithAffiliations.PubSubRequestComplete.send')
    def test_getAffiliationsForJid_notSupported(self, sendMock):
        xml = """
        <iq type='error'
            from='pubsub.shakespeare.lit'
            to='francisco@denmark.lit/barracks'
            id='affil1'>
          <error type='cancel'>
            <feature-not-implemented xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/>
            <unsupported xmlns='http://jabber.org/protocol/pubsub#errors'
                         feature='retrieve-affiliations'/>
          </error>
        </iq>
        """
        el = parseXml(xml)
        sendMock.side_effect = utils.good_side_effect(el)
        xs = Mock()
        d = psaff.getAffiliationsForJid(jid.JID('francisco@denmark.lit'), xs)

        # wokkel doesn't account for this situation yet
        return self.assertFailure(d, AttributeError)
        
    @patch('collab.pubsubRequestWithAffiliations.PubSubRequestComplete.send')
    def test_getSubscriptions_current(self, sendMock):
        xml = """
        <iq type='result'
            from='pubsub.shakespeare.lit'
            to='hamlet@denmark.lit/elsinore'
            id='subman1'>
          <pubsub xmlns='http://jabber.org/protocol/pubsub#owner'>
            <subscriptions node='princely_musings'>
              <subscription jid='hamlet@denmark.lit' subscription='subscribed'/>
              <subscription jid='polonius@denmark.lit' subscription='unconfigured'/>
              <subscription jid='bernardo@denmark.lit' subscription='subscribed' subid='123-abc'/>
              <subscription jid='bernardo@denmark.lit' subscription='subscribed' subid='004-yyy'/>
            </subscriptions>
          </pubsub>
        </iq>
        """
        el = parseXml(xml)
        sendMock.side_effect = utils.good_side_effect(el)
        xs = Mock()
        d = psaff.getSubscriptions(jid.JID('hamlet@denmark.lit/elsinore'), 'princely_musings', xs)

        def cb(subs):
            actual = [a.toElement().toXml() for a in subs]
            expected = [
                ps.Subscription(
                    nodeIdentifier=None,
                    subscriber=jid.internJID('hamlet@denmark.lit').userhostJID(),
                    state='subscribed'),
                ps.Subscription(
                    nodeIdentifier=None,
                    subscriber=jid.internJID('polonius@denmark.lit').userhostJID(),
                    state='unconfigured'),
                ps.Subscription(
                    nodeIdentifier=None,
                    subscriber=jid.internJID('bernardo@denmark.lit').userhostJID(),
                    state='subscribed',
                    subscriptionIdentifier='123-abc'),
                ps.Subscription(
                    nodeIdentifier=None,
                    subscriber=jid.internJID('bernardo@denmark.lit').userhostJID(),
                    state='subscribed',
                    subscriptionIdentifier='004-yyy'),
                ]
            self.assertEquals(len(actual), 4)
            for ex in expected:
                self.assertIn(ex.toElement().toXml(), actual)
            sendMock.assert_called_once_with(xs)

        d.addCallback(cb)
        return d
        
    @patch('collab.pubsubRequestWithAffiliations.PubSubRequestComplete.send')
    def test_getSubscriptionsForJid_current(self, sendMock):
        xml = """
        <iq type='result'
            from='pubsub.shakespeare.lit'
            to='francisco@denmark.lit'
            id='subscriptions1'>
          <pubsub xmlns='http://jabber.org/protocol/pubsub'>
            <subscriptions>
              <subscription node='node1' jid='francisco@denmark.lit' subscription='subscribed'/>
              <subscription node='node2' jid='francisco@denmark.lit' subscription='subscribed'/>
              <subscription node='node5' jid='francisco@denmark.lit' subscription='unconfigured'/>
              <subscription node='node6' jid='francisco@denmark.lit' subscription='subscribed' subid='123-abc'/>
              <subscription node='node6' jid='francisco@denmark.lit' subscription='subscribed' subid='004-yyy'/>
            </subscriptions>
          </pubsub>
        </iq>
        """
        el = parseXml(xml)
        sendMock.side_effect = utils.good_side_effect(el)
        xs = Mock()
        d = psaff.getSubscriptionsForJid(jid.JID('francisco@denmark.lit'), xs)

        def cb(subs):
            actual = [a.toElement().toXml() for a in subs]
            expected = [
                ps.Subscription(
                    nodeIdentifier='node1',
                    subscriber=jid.internJID('francisco@denmark.lit').userhostJID(),
                    state='subscribed'),
                ps.Subscription(
                    nodeIdentifier='node2',
                    subscriber=jid.internJID('francisco@denmark.lit').userhostJID(),
                    state='subscribed'),
                ps.Subscription(
                    nodeIdentifier='node5',
                    subscriber=jid.internJID('francisco@denmark.lit').userhostJID(),
                    state='unconfigured'),
                ps.Subscription(
                    nodeIdentifier='node6',
                    subscriber=jid.internJID('francisco@denmark.lit').userhostJID(),
                    state='subscribed',
                    subscriptionIdentifier='123-abc'),
                ps.Subscription(
                    nodeIdentifier='node6',
                    subscriber=jid.internJID('francisco@denmark.lit').userhostJID(),
                    state='subscribed',
                    subscriptionIdentifier='004-yyy'),
                ]
            self.assertEquals(len(actual), 5)
            for ex in expected:
                self.assertIn(ex.toElement().toXml(), actual)
            sendMock.assert_called_once_with(xs)

        d.addCallback(cb)
        return d
        
    @patch('collab.pubsubRequestWithAffiliations.PubSubRequestComplete.send')
    def test_getSubscriptionsForJid_none(self, sendMock):
        xml = """
        <iq type='result'
            from='pubsub.shakespeare.lit'
            to='francisco@denmark.lit/barracks'
            id='subscriptions1'>
          <pubsub xmlns='http://jabber.org/protocol/pubsub'>
            <subscriptions/>
          </pubsub>
        </iq>
        """
        el = parseXml(xml)
        sendMock.side_effect = utils.good_side_effect(el)
        xs = Mock()
        d = psaff.getSubscriptionsForJid(jid.JID('francisco@denmark.lit'), xs)

        def cb(subs):
            self.assertEquals(len(subs), 0)
            sendMock.assert_called_once_with(xs)

        d.addCallback(cb)
        return d
        
