# Copyright (c) Simon Parry.
# See LICENSE for details.

#tests for the gcSimulator
from collections import defaultdict
from datetime import datetime

from twisted.trial import unittest
from twisted.words.xish.domish import Element

import collab
from collab import simulation


class ParametersTests(unittest.TestCase):

    timeout = 2

    def test_init_defaults(self):
        p = simulation.Parameters()
        self.assertEquals(p.run_id, '0')
        self.assertEquals(p.output, '')
        self.assertEquals(p.number_runs, 1000000)
        self.assertEquals(p.cmd, 'info')
        self.assertTrue(p.timestamp is not None)

    def test_init_bounds(self):
        p = simulation.Parameters(number_runs=-1000)
        self.assertEquals(p.number_runs, 1000)
        
    def test_init_badCommand(self):
        def doIt():
            p = simulation.Parameters(cmd='wrong')

        self.assertRaises(simulation.InvalidParametersError, doIt)

    def test_setCommand(self):
        p = simulation.Parameters()
        self.assertEquals(p.cmd, 'info')

        p.setCommand('start')
        self.assertEquals(p.cmd, 'start')

    def test_setCommand_wrong(self):
        p = simulation.Parameters()
        self.assertEquals(p.cmd, 'info')

        def doIt():
            p.setCommand('wrong')

        self.assertRaises(simulation.InvalidParametersError, doIt)

    def test_toElement(self):
        dt = datetime.now()
        p = simulation.Parameters('100', 'output', 1000, 'start', dt)
        el = p.toElement()

        expected = Element((collab.COLLAB_NS, 'simulation'))
        params = expected.addElement('parameters')
        params.addElement('run_id', content='100')
        params.addElement('output', content='output')
        params.addElement('number_runs', content='1000')
        params.addElement('command', content='start')
        params.addElement('timestamp', content=str(dt))

        self.assertEquals(el.toXml(), expected.toXml())
        
    def test_fromElement(self):
        dt = datetime.now()
        el = Element((collab.COLLAB_NS, 'simulation'))
        params = el.addElement('parameters')
        params.addElement('run_id', content='100')
        params.addElement('output', content='output')
        params.addElement('number_runs', content='1000')
        params.addElement('command', content='start')
        params.addElement('timestamp', content=str(dt))

        p = simulation.Parameters.fromElement(el)
        self.assertEquals(p.run_id, '100')
        self.assertEquals(p.output, 'output')
        self.assertEquals(p.number_runs, 1000)
        self.assertEquals(p.cmd, 'start')
        self.assertEquals(p.timestamp, dt)

    def test_fromElement_defaults(self):
        dt = datetime.now()
        el = Element((collab.COLLAB_NS, 'simulation'))
        params = el.addElement('parameters')

        p = simulation.Parameters.fromElement(el)
        self.assertEquals(p.run_id, '0')
        self.assertEquals(p.output, '')
        self.assertEquals(p.number_runs, 1000000)
        self.assertEquals(p.cmd, 'info')
        self.assertTrue(p.timestamp is not None)

    def test_fromElement_wrongXml(self):
        dt = datetime.now()
        el = Element((collab.COLLAB_NS, 'simulation'))
        params = el.addElement('wrong parameters')
        params.addElement('run_id', content='100')
        params.addElement('output', content='output')
        params.addElement('number_runs', content='1000')
        params.addElement('command', content='start')
        params.addElement('timestamp', content=str(dt))

        def doIt():
            p = simulation.Parameters.fromElement(el)

        self.assertRaises(simulation.InvalidParametersError, doIt)

    def test_fromElement_wrongCommand(self):
        dt = datetime.now()
        el = Element((collab.COLLAB_NS, 'simulation'))
        params = el.addElement('parameters')
        params.addElement('run_id', content='100')
        params.addElement('output', content='output')
        params.addElement('number_runs', content='1000')
        params.addElement('command', content='wrong')
        params.addElement('timestamp', content=str(dt))

        def doIt():
            p = simulation.Parameters.fromElement(el)

        self.assertRaises(simulation.InvalidParametersError, doIt)
        
    def test_fromElement_notTopNode(self):
        dt = datetime.now()
        el = Element(('http://jabber.org/protocol/pubsub#event', 'item'))
        sim = el.addElement(name='simulation', defaultUri=collab.COLLAB_NS)
        params = sim.addElement('parameters')
        params.addElement('run_id', content='100')
        params.addElement('output', content='output')
        params.addElement('number_runs', content='1000')
        params.addElement('command', content='start')
        params.addElement('timestamp', content=str(dt))

        p = simulation.Parameters.fromElement(el)
        self.assertEquals(p.run_id, '100')
        self.assertEquals(p.output, 'output')
        self.assertEquals(p.number_runs, 1000)
        self.assertEquals(p.cmd, 'start')
        self.assertEquals(p.timestamp, dt)


def add(el, m, name):
    h = el.addElement('histogram')
    h['name'] = name
    for i in xrange(10):
        d_el = h.addElement('data')
        d_el['point'] = str(i)
        d_el['value'] = str(m*i)

class DistributionsTests(unittest.TestCase):
    """
    DistributionsTests: Tests for the L{simulation.Distributions} class
    
    """
    
    timeout = 2
    
    def setUp(self):
    	pass
    
    def tearDown(self):
    	pass    

    def test_defaults(self):
        d = simulation.Distributions()
        self.assertEquals(d.histograms, {})

    def test_combine_notAlreadyThere(self):
        d = simulation.Distributions()
        name = 'test'
        dist = defaultdict(int)
        for i in xrange(10):
            dist[i] = 2*i

        d.combine(name, dist)
        self.assertTrue(name in d.histograms)
        self.assertEquals(len(d.histograms), 1)
        h = d.histograms[name]
        for i in xrange(10):
            self.assertTrue(i in h)
            self.assertEquals(h[i], 2*i)

    def test_combine_alreadyThere(self):
        d = simulation.Distributions()
        name = 'test'
        dist1 = defaultdict(int)
        for i in xrange(10):
            dist1[i] = i
        dist2 = defaultdict(int)
        for i in xrange(10):
            dist2[i] = i

        d.combine(name, dist1)
        d.combine(name, dist2)
        self.assertTrue(name in d.histograms)
        self.assertEquals(len(d.histograms), 1)
        h = d.histograms[name]
        for i in xrange(10):
            self.assertTrue(i in h)
            self.assertEquals(h[i], 2*i)

    def test_toElement(self):
        d = simulation.Distributions()
        name1 = 'test1'
        dist1 = defaultdict(int)
        for i in xrange(10):
            dist1[i] = 2*i

        name2 = 'test2'
        dist2 = defaultdict(int)
        for i in xrange(10):
            dist2[i] = 3*i

        d.combine(name1, dist1)
        d.combine(name2, dist2)

        el = d.toElement()

        expected = Element((collab.COLLAB_NS, 'distributions'))
        add(expected, 2, name1)
        add(expected, 3, name2)

        self.assertEquals(el.toXml(), expected.toXml())

    def test_fromElement(self):
        name1 = 'bender1'
        name2 = 'bender2'

        el = Element((collab.COLLAB_NS, 'distributions'))
        add(el, 2, name1)
        add(el, 3, name2)

        d = simulation.Distributions.fromElement(el)
        self.assertTrue(name1 in d.histograms)
        self.assertTrue(name2 in d.histograms)
        self.assertEquals(len(d.histograms), 2)

        hist1 = d.histograms[name1]
        for i in xrange(10):
            self.assertTrue(i in hist1)
            self.assertEquals(hist1[i], 2*i)

        hist2 = d.histograms[name2]
        for i in xrange(10):
            self.assertTrue(i in hist2)
            self.assertEquals(hist2[i], 3*i)

    def test_fromElement_notTopElement(self):
        name1 = 'bender1'
        name2 = 'bender2'

        el = Element(('http://jabber.org/protocol/pubsub#event', 'item'))
        dist = el.addElement(name='distributions', defaultUri=collab.COLLAB_NS)
        add(dist, 2, name1)
        add(dist, 3, name2)

        d = simulation.Distributions.fromElement(el)
        self.assertTrue(name1 in d.histograms)
        self.assertTrue(name2 in d.histograms)
        self.assertEquals(len(d.histograms), 2)

        hist1 = d.histograms[name1]
        for i in xrange(10):
            self.assertTrue(i in hist1)
            self.assertEquals(hist1[i], 2*i)

        hist2 = d.histograms[name2]
        for i in xrange(10):
            self.assertTrue(i in hist2)
            self.assertEquals(hist2[i], 3*i)

    def test_fromElement_wrongTopElement(self):
        name = 'bender'
        el = Element((collab.COLLAB_NS, 'wrong'))
        h = el.addElement('histogram')
        h['name'] = name
        for i in xrange(10):
            d_el = h.addElement('data')
            d_el['point'] = str(i)
            d_el['value'] = str(2*i)


        def doIt():
            d = simulation.Distributions.fromElement(el)
        self.assertRaises(simulation.InvalidDistributionsError, doIt)

    def test_fromElement_noHistograms(self):
        name = 'bender'
        el = Element((collab.COLLAB_NS, 'distributions'))
        h = el.addElement('wrong')
        h['name'] = name
        for i in xrange(10):
            d_el = h.addElement('data')
            d_el['point'] = str(i)
            d_el['value'] = str(2*i)

        d = simulation.Distributions.fromElement(el)
        self.assertTrue(name not in d.histograms)
        self.assertEquals(d.histograms, {})

    def test_fromElement_wrongNameElement(self):
        name = 'bender'
        el = Element((collab.COLLAB_NS, 'distributions'))
        h = el.addElement('histogram')
        h['wrong'] = name
        for i in xrange(10):
            d_el = h.addElement('data')
            d_el['point'] = str(i)
            d_el['value'] = str(2*i)


        def doIt():
            d = simulation.Distributions.fromElement(el)
        self.assertRaises(simulation.InvalidDistributionsError, doIt)

    def test_fromElement_wrongPointElement(self):
        name = 'bender'
        el = Element((collab.COLLAB_NS, 'distributions'))
        h = el.addElement('histogram')
        h['name'] = name
        for i in xrange(10):
            d_el = h.addElement('data')
            d_el['wrong'] = str(i)
            d_el['value'] = str(2*i)


        def doIt():
            d = simulation.Distributions.fromElement(el)
        self.assertRaises(simulation.InvalidDistributionsError, doIt)

    def test_fromElement_wrongValueElement(self):
        name = 'bender'
        el = Element((collab.COLLAB_NS, 'distributions'))
        h = el.addElement('histogram')
        h['name'] = name
        for i in xrange(10):
            d_el = h.addElement('data')
            d_el['point'] = str(i)
            d_el['wrong'] = str(2*i)


        def doIt():
            d = simulation.Distributions.fromElement(el)
        self.assertRaises(simulation.InvalidDistributionsError, doIt)

    def test_fromElement_wrongPointData(self):
        name = 'bender'
        el = Element((collab.COLLAB_NS, 'distributions'))
        h = el.addElement('histogram')
        h['name'] = name
        for i in xrange(10):
            d_el = h.addElement('data')
            d_el['point'] = 'wrong'
            d_el['value'] = str(2*i)


        def doIt():
            d = simulation.Distributions.fromElement(el)
        self.assertRaises(simulation.InvalidDistributionsError, doIt)

    def test_fromElement_wrongValueData(self):
        name = 'bender'
        el = Element((collab.COLLAB_NS, 'distributions'))
        h = el.addElement('histogram')
        h['name'] = name
        for i in xrange(10):
            d_el = h.addElement('data')
            d_el['point'] = str(i)
            d_el['value'] = 'wrong'


        def doIt():
            d = simulation.Distributions.fromElement(el)
        self.assertRaises(simulation.InvalidDistributionsError, doIt)

    def test_fromElement_ignoresNonData(self):
        name = 'bender'
        el = Element((collab.COLLAB_NS, 'distributions'))
        h = el.addElement('histogram')
        h['name'] = name
        for i in xrange(10):
            if i%2:
                d_el = h.addElement('ignored')
                d_el['point'] = str(i)
                d_el['value'] = str(2*i)
            else:
                d_el = h.addElement('data')
                d_el['point'] = str(i)
                d_el['value'] = str(2*i)

        d = simulation.Distributions.fromElement(el)
        self.assertTrue(name in d.histograms)
        self.assertEquals(len(d.histograms), 1)
        hist = d.histograms[name]
        
        for i in xrange(10):
            if i%2:
                self.assertTrue(i not in hist)
            else:
                self.assertTrue(i in hist)
                self.assertEquals(hist[i], 2*i)

class ProgressTests(unittest.TestCase):
    """
    ProgressTests: Tests for the L{simulation.Progress} class
    
    """
    
    timeout = 2
    
    def setUp(self):
    	pass
    
    def tearDown(self):
    	pass
    
    def test_defaults(self):
        p = simulation.Progress()
        self.assertEquals(p.runs, 0)

    def test_toElement(self):
        p = simulation.Progress(100)
        el = p.toElement()

        expected = Element((collab.COLLAB_NS, 'progress'))
        expected.addElement('runs', content='100')

        self.assertEquals(el.toXml(), expected.toXml())

    def test_fromElement(self):
        el = Element((collab.COLLAB_NS, 'progress'))
        el.addElement('runs', content='100')

        p = simulation.Progress.fromElement(el)
        self.assertEquals(p.runs, 100)

    def test_fromElement_notTopNode(self):
        el = Element(('http://jabber.org/protocol/pubsub#event', 'item'))
        prog = el.addElement('progress', defaultUri=collab.COLLAB_NS)
        prog.addElement('runs', content='100')

        p = simulation.Progress.fromElement(el)
        self.assertEquals(p.runs, 100)

    def test_fromElement_noRuns(self):
        el = Element((collab.COLLAB_NS, 'progress'))
        el.addElement('score', content='100')

        p = simulation.Progress.fromElement(el)
        self.assertEquals(p.runs, 0)

    def test_fromElement_bad(self):
        el = Element((collab.COLLAB_NS, 'wrong'))
        el.addElement('runs', content='100')

        def doIt():
            p = simulation.Progress.fromElement(el)
        self.assertRaises(simulation.InvalidProgressError, doIt)


class LoggerTests(unittest.TestCase):
    """
    LoggerTests: Tests for the L{simulation.Logger} class
    
    """
    
    timeout = 2
    
    def setUp(self):
    	pass
    
    def tearDown(self):
    	pass
    
    def test_addLog(self):
        l = simulation.Logger()
        self.assertEquals(l.logs, defaultdict(list))

        l.addLog('error', 'this is an error')
        l.addLog('error', 'another one')
        l.addLog('warning', 'a warning')

        self.assertEquals(len(l.logs['error']), 2)
        self.assertEquals(len(l.logs['warning']), 1)
        self.assertEquals(l.logs['error'][0], 'this is an error')
        self.assertEquals(l.logs['error'][1], 'another one')
        self.assertEquals(l.logs['warning'][0], 'a warning')
    
    def test_hasSeverity(self):
        l = simulation.Logger()
        self.assertFalse(l.hasSeverity('error'))
        l.addLog('error', 'this is an error')
        self.assertTrue(l.hasSeverity('error'))
    
    def test_toElement(self):
        l = simulation.Logger()

        l.addLog('error', 'this is an error')
        l.addLog('error', 'another one')
        l.addLog('warning', 'a warning')

        el = l.toElement()
        expected = Element((collab.COLLAB_NS, collab.LOGGER_EL))
        expected.addElement('warning', content='a warning')
        expected.addElement('error', content='this is an error')
        expected.addElement('error', content='another one')

        self.assertEquals(el.toXml(), expected.toXml())

    def test_fromElement(self):
        el = Element((collab.COLLAB_NS, collab.LOGGER_EL))
        el.addElement('warning', content='a warning')
        el.addElement('error', content='this is an error')
        el.addElement('error', content='another one')

        l = simulation.Logger.fromElement(el)
        self.assertEquals(len(l.logs['error']), 2)
        self.assertEquals(len(l.logs['warning']), 1)
        self.assertEquals(l.logs['error'][0], 'this is an error')
        self.assertEquals(l.logs['error'][1], 'another one')
        self.assertEquals(l.logs['warning'][0], 'a warning')

    def test_fromElement_notALogger(self):
        el = Element((collab.COLLAB_NS, 'wrong'))
        el.addElement('warning', content='a warning')
        el.addElement('error', content='this is an error')
        el.addElement('error', content='another one')

        def doIt():
            l = simulation.Logger.fromElement(el)

        self.assertRaises(simulation.InvalidLoggerError, doIt)

    def test_fromElement_notAtTop(self):
        el = Element(('another ns', 'item'))
        logger = el.addElement(collab.LOGGER_EL, defaultUri=collab.COLLAB_NS)
        logger.addElement('warning', content='a warning')
        logger.addElement('error', content='this is an error')
        logger.addElement('error', content='another one')

        l = simulation.Logger.fromElement(el)
        self.assertEquals(len(l.logs['error']), 2)
        self.assertEquals(len(l.logs['warning']), 1)
        self.assertEquals(l.logs['error'][0], 'this is an error')
        self.assertEquals(l.logs['error'][1], 'another one')
        self.assertEquals(l.logs['warning'][0], 'a warning')

    
