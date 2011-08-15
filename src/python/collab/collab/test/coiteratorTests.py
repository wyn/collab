# Copyright (c) Simon Parry.
# See LICENSE for details.

from mock import Mock
from twisted.internet import defer, task
from twisted.trial import unittest

from collab.test import utils


class CoiteratorTests(unittest.TestCase):
    """
    CoiteratorTests: Me figuring out coiterators
    
    """
    
    timeout = 2
    
    def setUp(self):
        self.clock = task.Clock()
        self.sch = utils.ClockScheduler(self.clock)
        self.coop = task.Cooperator(scheduler=self.sch.callLater)
        self.mock = Mock()
    
    def tearDown(self):
    	pass
    
    def func(self, ls):
        def gen():
            for i in xrange(4):
                if i%2 == 0:
                    ls.remove(i)
                yield defer.succeed('done %s: ' % i)

        d = self.coop.coiterate(gen())
        d.addCallback(lambda _: ls)
        return d
    
    def funcBad(self, ls):
        def gen():
            for i in xrange(4):
                d = defer.fail(ValueError('failed %s: ' % i))
                def eb(err):
                    if i%2 == 0:
                        ls.remove(i)

                d.addErrback(eb)
                yield d

        d = self.coop.coiterate(gen())
        d.addCallback(lambda _: ls)
        return d
    
    def funcGoodMock(self, ls):
        def succeed(*a, **kw):
            return defer.succeed('lush')
        
        self.mock.succeed = Mock(side_effect=succeed) # side effects get called each time, return_value is static
        def gen():
            for i in xrange(4):
                d = self.mock.succeed()
                def cb(data):
                    if i%2 == 0:
                        ls.remove(i)

                d.addCallback(cb)
                yield d

        d = self.coop.coiterate(gen())
        d.addCallback(lambda _: ls)
        return d
    
    def funcBadMock(self, ls):
        def fail(*a, **kw):
            return defer.fail(ValueError('failed', a, kw)) # side effects get called each time, return_value is static
        
        self.mock.fail = Mock(side_effect=fail)
        def gen():
            for i in xrange(4):
                d = self.mock.fail('hello', arg='world')
                def eb(err):
                    if i%2 == 0:
                        ls.remove(i)

                d.addErrback(eb)
                yield d

        d = self.coop.coiterate(gen())
        d.addCallback(lambda _: ls)
        return d

    def test_coiteratorYieldingDeferreds(self):

        ls = set([i for i in xrange(4)])
        d = self.func(ls)
        def check(data):
            self.assertIdentical(ls, data)
            self.assertEquals(data, set([1,3]))

        d.addCallback(check)
        self.clock.pump([1,1,1,1])
        return d

    def test_coiteratorYieldingDeferreds_goodMock(self):

        ls = set([i for i in xrange(4)])
        d = self.funcGoodMock(ls)
        def check(data):
            self.assertIdentical(ls, data)
            self.assertEquals(data, set([1,3]))

        d.addCallback(check)
        self.clock.pump([1,1,1,1])
        return d

    def test_coiteratorYieldingDeferreds_failure(self):

        ls = set([i for i in xrange(4)])
        d = self.funcBad(ls)
        def check(data):
            self.assertIdentical(ls, data)
            self.assertEquals(data, set([1,3]))

        d.addCallback(check)
        self.clock.pump([1,1,1,1])
        return d

    def test_coiteratorYieldingDeferreds_failureMock(self):

        ls = set([i for i in xrange(4)])
        d = self.funcBadMock(ls)
        def check(data):
            self.assertIdentical(ls, data)
            self.assertEquals(data, set([1,3]))

        d.addCallback(check)
        self.clock.pump([1,1,1,1])
        return d
