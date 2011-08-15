# Copyright (c) Simon Parry.
# See LICENSE for details.

from twisted.python import log
from twisted.words.protocols.jabber import jid

from collab import correlatedDefaultsSimulator as mng
from collab.tapfiles import baseTap as base

class Options(base.Options):
    def __init__(self):
        super(Options, self).__init__()


def makeService(config):
    # create XMPP external component
    s, cs = base.makeServiceAndComponent(config)

    j = config['jid']
    log.msg('Creating Simulations Manager')
    mngr = mng.CorrelatedDefaultsSimulator(jid=jid.JID(j), name='Simulations Manager')
    mngr.setHandlerParent(cs)

    return s
