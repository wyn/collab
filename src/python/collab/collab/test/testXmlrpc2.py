# Copyright (c) Simon Parry.
# See LICENSE for details.

# from twisted.web.xmlrpc import Proxy
# from twisted.internet import reactor

# def printValue(value):
#     print repr(value)
#     reactor.stop()

# def printError(error):
#     print 'error', error
#     reactor.stop()

# proxy = Proxy('http://127.0.0.1:4560/RPC2')
# proxy.callRemote('status').addCallbacks(printValue, printError)
# reactor.run()

import xmlrpclib

server_url = 'http://127.0.0.1:4560';
server = xmlrpclib.Server(server_url);

params = {}
# params["user"] = "ggeo"
# params["host"] = "master.local"
# params["password"] = "gogo11"

result = server.status(params)
print result
