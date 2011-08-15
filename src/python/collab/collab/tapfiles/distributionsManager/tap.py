# Copyright (c) Simon Parry.
# See LICENSE for details.

from twisted.python import log
from twisted.words.protocols.jabber import jid

from collab import distributionsManager as mng
from collab.tapfiles import baseTap as base

class Options(base.Options):
    def __init__(self):
        super(Options, self).__init__()


def makeService(config):
    # create XMPP external component
    s, cs = base.makeServiceAndComponent(config)

    j = config['jid']
    log.msg('Creating Distributions Manager')
    mngr = mng.DistributionsManager(jid=jid.JID(j), name='Distributions Manager')
    mngr.setHandlerParent(cs)

    return s
