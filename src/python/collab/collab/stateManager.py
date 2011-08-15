# Copyright (c) Simon Parry.
# See LICENSE for details.

#Everything to do with managing state for xmpp ad-hoc command wizards
import copy
from datetime import datetime

from twisted.internet import defer, threads
from twisted.python import log
from twisted.words.protocols.jabber import error, jid
from wokkel import pubsub as ps
from zope.interface import implements, Interface

import collab
from collab import simulation as sim, portfolio as port, pubsubRequestWithAffiliations as psaff


class StateChangerError(Exception):
    pass


class IStateChanger(Interface):
    def isValid():
        pass

    def commit():
        pass

    def add(field, val):
        pass

    def reset():
        pass
    
class StateChangerBase(object):
    """
    Base class for all StateChangers
    Need to overwrite whatever happens on commit
    """
    implements(IStateChanger)

    def __init__(self, requiredFields):
        self.requiredFields = requiredFields
        self.data = {}

    def isValid(self):
        for r in self.requiredFields:
            if r not in self.data:
                return False
        return True

    def commit(self):
        pass

    def add(self, field, val):
        if field in self.requiredFields:
            if field not in self.data:
                self.data[field] = None
            self.data[field] = val

    def reset(self):
        self.data = {}

class RegisterMachineStateChanger(StateChangerBase):

    def __init__(self, xmlrpc):
        super(RegisterMachineStateChanger, self).__init__(['machine'])
        self.xmlrpc = xmlrpc

    def commit(self):
        return threads.deferToThread(self.xmlrpc.host_register, {'host': self.data['machine']})

class UnregisterMachineStateChanger(StateChangerBase):
    def __init__(self, xmlrpc):
        super(UnregisterMachineStateChanger, self).__init__(['machines'])
        self.xmlrpc = xmlrpc

    def commit(self):
        ds = []
        for val in self.data['machines']:
            if val not in set([collab.COLLAB_HOST, collab.MAIN_HOST]):
                ds.append(threads.deferToThread(self.xmlrpc.host_remove, {'host': val}))
        return defer.DeferredList(ds)

class CreateCollabNodeStateChanger(StateChangerBase):
    def __init__(self):
        super(CreateCollabNodeStateChanger, self).__init__(['component', 'machine'])

    def commit(self):
        comp = self.data['component']
        mach = self.data['machine']
        # initialise comp on mach
        log.msg('Create Collab component %s on %s' % (comp, mach))
        return defer.succeed(None)

@defer.inlineCallbacks
def manageAffiliations(sender, name, pubs, admins, xs, includeAdmin=False):
    # set up affiliations, least significant first so that more significant with same key
    # overwrite ones that are less significant
    specials = set([sender.full(), collab.ADMIN_JID])

    affiliations = {}
    def setAffiliation(j, aff):
        affiliations[j] = aff

    old_affs = yield psaff.getAffiliations(
        sender=sender,
        node=name,
        xs=xs            
        )

    log.msg('old affiliations %s' % old_affs)
    [setAffiliation(j.full(), u'none') for j, aff in old_affs.iteritems() if j.full() not in specials]

    if len(affiliations) > 0:
        yield psaff.makeAffiliations(
            sender=sender,
            node=name,
            affiliations=affiliations,
            xs=xs)

    affiliations = {}
    [setAffiliation(p, u'publisher') for p in pubs if p not in specials]
    [setAffiliation(a, u'owner') for a in admins if a not in specials]

    if includeAdmin:
        affiliations[collab.ADMIN_JID] = u'owner'

    if len(affiliations) > 0:
        yield psaff.makeAffiliations(
            sender=sender,
            node=name,
            affiliations=affiliations,
            xs=xs)

@defer.inlineCallbacks
def manageSubscriptions(sender, name, subs, xs):
    old_subscriptions = yield psaff.getSubscriptions(
        sender=sender,
        node=name,
        xs=xs)

    old_subs = set()
    for s in old_subscriptions:
        s.state = 'none'
        old_subs.add(s)

    if len(old_subs) > 0:
        yield psaff.makeSubscriptions(
            sender=sender,
            node=name,
            subscriptions=old_subs,
            xs=xs)

    new_subs = set()
    for s in subs:
        new_subs.add(ps.Subscription(
            nodeIdentifier=None, subscriber=s, state='subscribed'
            ))

    if len(new_subs) > 0:
        yield psaff.makeSubscriptions(
            sender=sender,
            node=name,
            subscriptions=new_subs,
            xs=xs)


@defer.inlineCallbacks
def makePSNode(sender, suggested_name, psclient, max_tries=100):
    # find out if name is OK or generate new one using component
    # create new ps node with that name
    # set admins and pubs
    i, not_ok, name = 0, True, suggested_name
    while not_ok and i < max_tries:
        try:
            yield psclient.createNode(
                service=jid.JID(collab.PUBSUB_NODE),
                nodeIdentifier=name,
                options=dict({'pubsub#persist_items': 0}),
                sender=sender
            )
            not_ok = False
        except error.StanzaError as e:
            if e.condition == 'conflict':
                log.msg('node %s already exists' % suggested_name)
                name = suggested_name + str(i)
                i += 1
    if not_ok:
        raise error.StanzaError(
            'Cannot create node %s after %s tries, quitting' % (suggested_name, max_tries)
            )

    defer.returnValue(name)

    
class CreatePubsubNodeStateChanger(StateChangerBase):
    def __init__(self, psclient, jid):
        super(CreatePubsubNodeStateChanger, self).__init__(['component', 'name', 'admins', 'publishers', 'subscribers'])
        self.psclient = psclient
        self.jid = jid

    def commit(self):
        comp = self.data['component']
        suggested_name = self.data['name']
        admins = self.data['admins']
        pubs = self.data['publishers']
        subs = self.data['subscribers']

        log.msg('Creating channel %s based on %s' % (suggested_name, comp))
        [log.msg('Admins: %s' % a) for a in admins]
        [log.msg('Publishers: %s' % a) for a in pubs]
        [log.msg('Subscribers: %s' % a) for a in subs]

        d = makePSNode(self.jid, suggested_name, self.psclient)
        def manageRest(name):
            ds = []
            ds.append(manageAffiliations(self.jid, name, pubs, admins, self.psclient.xmlstream, True))
            ds.append(manageSubscriptions(self.jid, name, subs, self.psclient.xmlstream))
            return defer.DeferredList(ds)

        d.addCallback(manageRest)
        return d

class ConfigPubsubNodeStateChanger(StateChangerBase):
    def __init__(self, psclient, jid):
        super(ConfigPubsubNodeStateChanger, self).__init__(['name', 'admins', 'publishers', 'subscribers'])
        self.psclient = psclient
        self.jid = jid

    def commit(self):
        name = self.data['name']
        admins = self.data['admins']
        pubs = self.data['publishers']
        subs = self.data['subscribers']

        log.msg('Configuring channel %s' % name)
        [log.msg('Admins: %s' % a) for a in admins]
        [log.msg('Publishers: %s' % a) for a in pubs]
        [log.msg('Subscribers: %s' % a) for a in subs]

        ds = []
        ds.append(manageAffiliations(self.jid, name, pubs, admins, self.psclient.xmlstream))
        ds.append(manageSubscriptions(self.jid, name, subs, self.psclient.xmlstream))
        return defer.DeferredList(ds)
                  
        
class DeletePubsubNodeStateChanger(StateChangerBase):
    def __init__(self, psclient, jid):
        super(DeletePubsubNodeStateChanger, self).__init__(['name'])
        self.psclient = psclient
        self.jid = jid

    def commit(self):
        names = self.data['name']

        ds = []
        for name in names:
            log.msg('Deleting channel %s' % name)
            ds.append(self.psclient.deleteNode(
                service=jid.JID(collab.PUBSUB_NODE),
                nodeIdentifier=name
                ))

        return defer.DeferredList(ds)

    
class ConfigureLoadBalancerStateChanger(StateChangerBase):
    def __init__(self, loadBalancer):
        super(ConfigureLoadBalancerStateChanger, self).__init__(['frequency'])
        self.loadBalancer = loadBalancer

    def commit(self):
        freq = max(float(self.data['frequency']), 1.0)
        if self.loadBalancer.running:
            self.loadBalancer.stop()
        return self.loadBalancer.start(freq)

    
class LHPPortfolioStateChanger(StateChangerBase):
    """
    LHPPortfolioStateChanger: State changer for the LHP simulation
    
    """
    def __init__(self, broadcaster):
        super(LHPPortfolioStateChanger, self).__init__(['default_probability', 'base_correlation', 'number_issuers', 'number_runs'])
        self.broadcaster = broadcaster

    def _makePortfolio(self, corr, dp, n):
        f = port.Factor('factor', corr)
        assets = set()
        for a in xrange(n-1):
            iss = port.Issuer('issuer%s' % a, set([f]))
            assets.add(port.Asset('asset%s' % a, dp, issuer=iss))

        return port.Portfolio('portfolio', assets)

    def commit(self):
        dp = float(self.data['default_probability'])
        corr = float(self.data['base_correlation'])
        num_issuers = int(self.data['number_issuers'])
        num_runs = int(self.data['number_runs'])

        run_id = 'lhp_%s' % datetime.now()
        params = sim.Parameters(run_id=run_id, number_runs=max(num_runs, 10000), cmd='start')
        p = self._makePortfolio(corr, dp, num_issuers)
        return self.broadcaster(params, p)
        
class ClientRegisterStateChanger(StateChangerBase):
    """
    ClientRegisterStateChanger: State changer for the LHP simulation
    
    """
    def __init__(self, registration):
        super(ClientRegisterStateChanger, self).__init__(['client_jid'])
        self.registration = registration

    def commit(self):
        j = jid.JID((self.data['client_jid']))
        return self.registration(j)
        

class NullStateChanger(StateChangerBase):
    """
    NullStateChanger: State changer that doesn't do anything
    Useful for pages/wizards that just display stuff

    """
    def __init__(self):
        super(NullStateChanger, self).__init__([])

    def commit(self):
        return defer.succeed(None)

        
class StateManagerError(Exception):
    pass

class EmptyStateManagerError(StateManagerError):
    pass

class InvalidStateError(StateManagerError):
    pass

class StateMerger(object):

    def __init__(self):
        self.states = []
        self.data = {}

    def merge(self, state):
        for field, val in state.iteritems():
            if field not in self.data:
                self.data[field] = None
            self.data[field] = val
        self.states.append(copy.deepcopy(self.data))

    def reset(self):
        self.states = []
        self.data = {}


class IStateManager(Interface):
    def reset():
        pass

    def head():
        pass

    def push(s):
        pass

    def commit():
        pass

    def penultimateState():
        pass

class StateManager(object):
    implements(IStateManager)

    def __init__(self, stateChanger, stateMerger=None):
        self.stateChanger = stateChanger
        self.stateMerger = stateMerger or StateMerger()
        
    def reset(self):
        self.stateMerger.reset()
        self.stateChanger.reset()

    def head(self):
        if not self.stateMerger.states:
            raise EmptyStateManagerError('No more data history')
        return self.stateMerger.states[-1]

    def push(self, s):
        self.stateMerger.merge(s)

    def commit(self):
        for field, val in self.head().iteritems():
            self.stateChanger.add(field, val)

        if not self.stateChanger.isValid():
            return defer.fail(InvalidStateError('Cannot commit with invalid data'))

        return self.stateChanger.commit()

    def penultimateState(self):
        if len(self.stateMerger.states) <= 1:
            raise EmptyStateManagerError('No penultimate data history')

        self.stateMerger.states.pop()
        return self.stateMerger.states.pop()
    
    
    
