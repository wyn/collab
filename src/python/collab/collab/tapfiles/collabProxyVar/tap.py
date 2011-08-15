# Copyright (c) Simon Parry.
# See LICENSE for details.

from twisted.python import log
from twisted.words.protocols.jabber import jid

from collab import proxy as mng
from collab.tapfiles import baseTap as base

class Options(base.Options):
    def __init__(self):
        super(Options, self).__init__()


def makeService(config):
    # create XMPP external component
    s, cs = base.makeServiceAndComponent(config)

    j = config['jid']
    log.msg('Creating Collab VaR Proxy')
    mngr = mng.CollabProxy(jid=jid.JID(j), name='Collab VaR Proxy')
    mngr.setHandlerParent(cs)

    return s
