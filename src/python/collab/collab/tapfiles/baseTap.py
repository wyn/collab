# Copyright (c) Simon Parry.
# See LICENSE for details.

#tap file for the gcPortfolioManager service
from twisted.application import service
from twisted.python import usage
from wokkel import component
from wokkel.disco import DiscoHandler
from wokkel.generic import FallbackHandler


class Options(usage.Options):

    optParameters = [
        ('jid', None, None, 'JID of the component'),
        ('secret', None, 'pass', 'Password for the component'),
        ('rhost', None, '127.0.0.1', 'Ejabberd server address'),
        ('rport', None, '10001', 'Ejabberd server port to connect on'),
    ]
  
    optFlags = [
        ('verbose', 'v', 'Show traffic'),
    ]
  
    def postOptions(self):
        try:
            self['rport'] = int(self['rport'])
        except ValueError:
            pass

def makeServiceAndComponent(config):
    s = service.MultiService()

    # create XMPP external component
    cs = component.Component(config['rhost'], config['rport'], config['jid'], config['secret'])
    if config['verbose']:
        cs.logTraffic = True

    # wait for no more than 15 minutes to try to reconnect
    cs.factory.maxDelay = 900
    cs.setServiceParent(s)

    FallbackHandler().setHandlerParent(cs)
    DiscoHandler().setHandlerParent(cs)

    return (s, cs)
