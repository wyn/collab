# Copyright (c) Simon Parry.
# See LICENSE for details.

import xmlrpclib

from twisted.internet import defer, threads
from twisted.trial import unittest
from twisted.web import xmlrpc


class MyQueryProtocol(xmlrpc.QueryProtocol):

    def connectionMade(self):
        self.sendCommand('POST', self.factory.path)
        self.sendHeader('User-Agent', 'Twisted/XMLRPClib')
        self.sendHeader('Host', self.factory.host+':4560')
        self.sendHeader('Content-type', 'text/xml')
        self.sendHeader('Content-length', str(len(self.factory.payload)))
        if self.factory.user:
            auth = '%s:%s' % (self.factory.user, self.factory.password)
            auth = auth.encode('base64').strip()
            self.sendHeader('Authorization', 'Basic %s' % (auth,))
        self.endHeaders()
        self.transport.write(self.factory.payload)
    
    
class xmlrpcTests(unittest.TestCase):
    """
    xmlrpcTests: Testing the XML RPC twisted functionality
    
    """
    
    timeout = 2
    
    def setUp(self):
    	self.twst = False
    
    def tearDown(self):
    	pass

    @defer.inlineCallbacks
    def test_xmlrpc(self):

        if self.twst:
            def printValue(value):
                print repr(value)

            def printError(error):
                print 'error', error

            p = xmlrpc.Proxy("http://127.0.0.1:4560/RPC2")
            p.queryFactory.protocol = MyQueryProtocol
            
#            p = xmlrpc.Proxy("http://time.xmlrpc.com/RPC2")
            t = yield p.callRemote("registered_users", "master.local")
#            t = yield p.callRemote("currentTime.getCurrentTime")
            print t

        else:
            server_url = 'http://127.0.0.1:4560';
            server = xmlrpclib.Server(server_url);
            server.__verbose = 1

            params = {}
            params["host"] = "master.local"
            # params["user"] = "ggeo"
            # params["host"] = "master.local"
            # params["password"] = "gogo11"

            result = yield threads.deferToThread(server.host_list, {})
            print result
