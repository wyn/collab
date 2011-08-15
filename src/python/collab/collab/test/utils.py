# Copyright (c) Simon Parry.
# See LICENSE for details.

import random
import xml.dom.minidom as x

from twisted.internet import reactor, task, defer
from twisted.python import log
from twisted.words.xish.domish import Element

import collab


num_issuers = 2
num_assets = 4
ratio = int(num_assets/num_issuers)
num_factors = 3
div = 10.0

class ClockScheduler(object):

    EPSILON = 0.00000001
    
    def __init__(self, clock):
        self.clock = clock

    def callLater(self, x):
        return self.clock.callLater(self.EPSILON, x)


def good_side_effect(ret_val):
    def inner(*a, **kw):
        return defer.succeed(ret_val)
    return inner

def bad_side_effect(err):
    def inner(*a, **kw):
        return defer.fail(err)
    return inner

def mockReturnValueLogger(nm):
    def prnt(msg):
        log.msg(msg)
        return msg
    return task.deferLater(reactor, 0, prnt, 'mocked return value: %s' % nm)

def mockReturnValueListLogger(nm):
    def prnt(msg):
        log.msg(msg)
        return msg
    return [task.deferLater(reactor, 0, prnt, 'mocked return value: %s' % nm)]

def prettyPrint(raw_xml):
    xml = x.parseString(raw_xml)
    return xml.toprettyxml()
    
def getPortfolio():
    portfolio = Element((collab.COLLAB_NS, 'portfolio'))
    #assets
    assets = portfolio.addElement('assets')
    for i in xrange(num_assets):
        a = assets.addElement('asset')
        a.addElement('id').addContent(str(i))
        a.addElement('name').addContent('asset%i' % i)
        a.addElement('default_probability').addContent(str(float(i)/div))
    #issuers
    issuers = portfolio.addElement('issuers')
    for i in xrange(num_issuers):
        iss = issuers.addElement('issuer')
        iss.addElement('id').addContent(str(i))
        iss.addElement('name').addContent('issuer%i' % i)
        fs = iss.addElement('factors')
        for j in xrange(num_factors):
            f = fs.addElement('factor')
            f.addElement('name').addContent('factor%i' % j)
            f.addElement('weight').addContent(str(float(j)/div))
    #asset issuer map
    aimap = portfolio.addElement('asset_issuer_map')
    for i in xrange(num_assets):
        a = aimap.addElement('asset')
        a.addElement('id').addContent(str(i))
        a.addElement('issuer').addElement('id').addContent(str(i%num_issuers))

    return portfolio

def getRandomPortfolio(min_size=10):
    portfolio = Element((collab.COLLAB_NS, 'portfolio'))
    #assets
    assets = portfolio.addElement('assets')
    no_assets = random.randrange(min_size,20)
    no_issuers = int(no_assets/ratio)
    for i in xrange(no_assets):
        a = assets.addElement('asset')
        a.addElement('id').addContent(str(i))
        a.addElement('name').addContent('asset%i' % i)
        a.addElement('default_probability').addContent(str(float(i)/div))
    #issuers
    issuers = portfolio.addElement('issuers')
    for i in xrange(no_issuers):
        iss = issuers.addElement('issuer')
        iss.addElement('id').addContent(str(i))
        iss.addElement('name').addContent('issuer%i' % i)
        fs = iss.addElement('factors')
        for j in xrange(random.randrange(1, 5)):
            f = fs.addElement('factor')
            f.addElement('name').addContent('factor%i' % j)
            f.addElement('weight').addContent(str(float(j)/div))
    #asset issuer map
    aimap = portfolio.addElement('asset_issuer_map')
    for i in xrange(no_assets):
        a = aimap.addElement('asset')
        a.addElement('id').addContent(str(i))
        a.addElement('issuer').addElement('id').addContent(str(i%no_issuers))

    return portfolio
