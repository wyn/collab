# Copyright (c) Simon Parry.
# See LICENSE for details.

#tests for the gcSimulator
from twisted.trial import unittest
from twisted.words.xish.domish import Element

import collab
from collab import portfolio, simulation


collabNs = collab.COLLAB_NS

def checkFactor(name, weight, factors):
    for f in factors:
        if f.name == name and f.weight == weight:
            return True
    return False


class AssetTests(unittest.TestCase):

    timeout = 2

    def test_AssetDefaults(self):
        a = portfolio.Asset('ass')
        self.assertEquals(1.0, a.dp)
        self.assertEquals(1.0, a.recovery)
        self.assertEquals(100.0, a.notional)
        self.assertTrue(a.issuer is None)

    def test_AssetBounds1(self):
        a = portfolio.Asset('ass', dp=2.0, recovery=-2.0)
        self.assertEquals(1.0, a.dp)
        self.assertEquals(0.0, a.recovery)
        self.assertEquals(100.0, a.notional)
        self.assertTrue(a.issuer is None)
        
    def test_AssetBounds2(self):
        a = portfolio.Asset('ass', dp=-2.0, recovery=2.0)
        self.assertEquals(0.0, a.dp)
        self.assertEquals(1.0, a.recovery)
        self.assertEquals(100.0, a.notional)
        self.assertTrue(a.issuer is None)

    def test_toElement(self):
        fs = set([portfolio.Factor('f1', 0.1)])
        i = portfolio.Issuer('iss', fs)
        a = portfolio.Asset('ass', issuer=i)
        el = a.toElement()

        expected = Element((collabNs, 'asset'))
        expected.addElement('name', content='ass')
        expected.addElement('dp', content='1.0')
        expected.addElement('recovery', content='1.0')
        expected.addElement('notional', content='100.0')

        i_el = expected.addElement('issuer')
        i_el.addElement('name', content='iss')
        fs_el = i_el.addElement('factors')
        f1_el = fs_el.addElement('factor')
        f1_el.addElement('name', content='f1')
        f1_el.addElement('weight', content='0.1')

        self.assertEquals(el.toXml(), expected.toXml())

    def test_toElement_noIssuer(self):
        a = portfolio.Asset('ass')
        el = a.toElement()

        expected = Element((collabNs, 'asset'))
        expected.addElement('name', content='ass')
        expected.addElement('dp', content='1.0')
        expected.addElement('recovery', content='1.0')
        expected.addElement('notional', content='100.0')

        self.assertEquals(el.toXml(), expected.toXml())
        self.assertEquals(el.uri, collabNs)
        
    def test_fromElement(self):
        el = Element((collabNs, 'asset'))
        el.addElement('name', content='ass')
        el.addElement('dp', content='0.1')
        el.addElement('recovery', content='0.1')
        el.addElement('notional', content='200.0')

        i_el = el.addElement('issuer')
        i_el.addElement('name', content='iss')
        fs_el = i_el.addElement('factors')
        f1_el = fs_el.addElement('factor')
        f1_el.addElement('name', content='f1')
        f1_el.addElement('weight', content='0.1')
        f2_el = fs_el.addElement('factor')
        f2_el.addElement('name', content='f2')
        f2_el.addElement('weight', content='0.2')

        ass = portfolio.Asset.fromElement(el)
        self.assertEquals(ass.name, 'ass')
        self.assertEquals(ass.dp, 0.1)       
        self.assertEquals(ass.recovery, 0.1)
        self.assertEquals(ass.notional, 200.0)       

        i = ass.issuer
        self.assertEquals(i.name, 'iss')
        
        fs = i.factors
        self.assertEquals(len(fs), 2)

        self.assertTrue(checkFactor('f1', 0.1, fs))
        self.assertTrue(checkFactor('f2', 0.2, fs))

    def test_fromElement_defaults(self):
        el = Element((collabNs, 'asset'))
        el.addElement('name', content='ass')

        ass = portfolio.Asset.fromElement(el)
        self.assertEquals(ass.name, 'ass')
        self.assertEquals(ass.dp, 1.0)       
        self.assertEquals(ass.recovery, 1.0)
        self.assertEquals(ass.notional, 100.0)
        self.assertTrue(ass.issuer is None)

    def test_fromElement_noName(self):
        el = Element((collabNs, 'asset'))
        def doIt():
            ass = portfolio.Asset.fromElement(el)

        self.assertRaises(portfolio.InvalidAssetError, doIt)

        
class IssuerTests(unittest.TestCase):

    timeout = 2

    def test_IssuerDefault(self):
        i = portfolio.Issuer('iss')
        self.assertEquals(i.factors, set())

    def test_Issuer_toElement(self):
        fs = set([portfolio.Factor('f1', 0.1)])
        i = portfolio.Issuer('iss', fs)
        el = i.toElement()

        expected = Element((collabNs, 'issuer'))
        expected.addElement('name', content='iss')
        fs_el = expected.addElement('factors')
        f1_el = fs_el.addElement('factor')
        f1_el.addElement('name', content='f1')
        f1_el.addElement('weight', content='0.1')

        self.assertEquals(el.toXml(), expected.toXml())
        self.assertEquals(el.uri, collabNs)
        
    def test_Issuer_fromElement(self):
        expected = Element((collabNs, 'issuer'))
        expected.addElement('name', content='iss')
        fs_el = expected.addElement('factors')
        f1_el = fs_el.addElement('factor')
        f1_el.addElement('name', content='f1')
        f1_el.addElement('weight', content='0.1')
        f2_el = fs_el.addElement('factor')
        f2_el.addElement('name', content='f2')
        f2_el.addElement('weight', content='0.2')

        i = portfolio.Issuer.fromElement(expected)
        self.assertEquals(i.name, 'iss')
        fs = i.factors
        self.assertEquals(len(fs), 2)

        self.assertTrue(checkFactor('f1', 0.1, fs))
        self.assertTrue(checkFactor('f2', 0.2, fs))

    def test_Issuer_fromElement_noName(self):
        expected = Element((collabNs, 'issuer'))
        fs_el = expected.addElement('factors')
        f1_el = fs_el.addElement('factor')
        f1_el.addElement('name', content='f1')
        f1_el.addElement('weight', content='0.1')
        f2_el = fs_el.addElement('factor')
        f2_el.addElement('name', content='f2')
        f2_el.addElement('weight', content='0.2')

        def doIt():
            i = portfolio.Issuer.fromElement(expected)

        self.assertRaises(portfolio.InvalidIssuerError, doIt)

    def test_Issuer_fromElement_noFactors(self):
        expected = Element((collabNs, 'issuer'))
        expected.addElement('name', content='iss')

        def doIt():
            i = portfolio.Issuer.fromElement(expected)

        self.assertRaises(portfolio.InvalidIssuerError, doIt)

    
    def test_Issuer_fromElement_factorsButNoneInThere(self):
        expected = Element((collabNs, 'issuer'))
        expected.addElement('name', content='iss')
        fs_el = expected.addElement('factors')

        i = portfolio.Issuer.fromElement(expected)
        self.assertEquals(i.name, 'iss')
        self.assertEquals(i.factors, set())


class FactorTests(unittest.TestCase):

    timeout = 2

    def test_bounds(self):
        f = portfolio.Factor('fac', 10.0)
        self.assertEquals(f.weight, 1.0)

        f = portfolio.Factor('fac', -10.0)
        self.assertEquals(f.weight, 0.0)

    def test_equality(self):
        f1 = portfolio.Factor('fac', 0.3)
        f2 = portfolio.Factor('fac', 0.4)
        self.assertTrue(f1 == f2)
        
    def test_toElement(self):
        f = portfolio.Factor('fac', 0.5)
        el = f.toElement()
        
        expected = Element((collabNs, 'factor'))
        expected.addElement('name', content='fac')
        expected.addElement('weight', content='0.5')

        self.assertEquals(el.toXml(), expected.toXml())
        self.assertEquals(el.uri, collabNs)

    def test_fromElement(self):
        el = Element((collabNs, 'factor'))
        el.addElement('name', content='fac')
        el.addElement('weight', content='0.5')

        f = portfolio.Factor.fromElement(el)
        self.assertEquals(f.name, 'fac')
        self.assertEquals(f.weight, 0.5)

    def test_fromElement_noName(self):
        el = Element((collabNs, 'factor'))
        el.addElement('weight', content='0.5')

        def doIt():
            f = portfolio.Factor.fromElement(el)

        self.assertRaises(portfolio.InvalidFactorError, doIt)

    def test_fromElement_noWeight(self):
        el = Element((collabNs, 'factor'))
        el.addElement('name', content='fac')

        def doIt():
            f = portfolio.Factor.fromElement(el)

        self.assertRaises(portfolio.InvalidFactorError, doIt)


class PortfolioTests(unittest.TestCase):

    timeout = 2

    def assertSets(self, s1, s2):
        self.assertEquals(len(s1), len(s2))
        [self.assertIn(s, s2) for s in s1]
            
    def test_PortfolioDefaults(self):
        p = portfolio.Portfolio('port')
        self.assertEquals(p.assets, set())
        self.assertEquals(p.issuers(), set())
        self.assertEquals(p.factors(), set())
        self.assertEquals(p.asset_issuer_map(), dict())

    def test_PortfolioNullIssuers(self):
        asses = set([
            portfolio.Asset('ass1'),
            portfolio.Asset('ass2'),
            portfolio.Asset('ass3')
            ])
        p = portfolio.Portfolio('port', asses)
        self.assertEquals(p.assets, asses)
        self.assertSets(p.issuers(), set())
        self.assertSets(p.factors(), set())
        self.assertEquals(p.asset_issuer_map(), dict())

    def test_PortfolioOneIssuerMultiFactors(self):
        fs = set([portfolio.Factor('f1', 0.1), portfolio.Factor('f2', 0.2), portfolio.Factor('f3', 0.3)])
        i = portfolio.Issuer('iss', fs)
        asses = set([
            portfolio.Asset('ass1', issuer=i),
            portfolio.Asset('ass2', issuer=i),
            portfolio.Asset('ass3', issuer=i)
            ])

        p = portfolio.Portfolio('port', asses)

        self.assertEquals(p.assets, asses)
        self.assertSets(p.issuers(), set([i]))
        self.assertSets(p.factors(), fs)
        self.assertEquals(p.asset_issuer_map(), dict([
            ('ass1', i),
            ('ass2', i),
            ('ass3', i)
            ]))

    def test_PortfolioMultiIssuersOneFactor(self):
        f = set([portfolio.Factor('f1', 0.1)])
        iss = [portfolio.Issuer('iss1', f), portfolio.Issuer('iss2', f), portfolio.Issuer('iss3', f)]
        asses = set([
            portfolio.Asset('ass1', issuer=iss[0]),
            portfolio.Asset('ass2', issuer=iss[1]),
            portfolio.Asset('ass3', issuer=iss[2])
            ])

        p = portfolio.Portfolio('port', asses)

        self.assertEquals(p.assets, asses)
        self.assertSets(p.issuers(), set(iss))
        self.assertSets(p.factors(), f)
        self.assertEquals(p.asset_issuer_map(), dict([
            ('ass1', iss[0]),
            ('ass2', iss[1]),
            ('ass3', iss[2])
            ]))

    def test_PortfolioMultiIssuersMultiFactors(self):
        fs = [portfolio.Factor('f1', 0.1), portfolio.Factor('f2', 0.2), portfolio.Factor('f3', 0.3)]
        iss = [portfolio.Issuer('iss1', set(fs[0:1])), portfolio.Issuer('iss2', set(fs[1:2])), portfolio.Issuer('iss3', set(fs))]
        asses = set([
            portfolio.Asset('ass1', issuer=iss[0]),
            portfolio.Asset('ass2', issuer=iss[1]),
            portfolio.Asset('ass3', issuer=iss[2]),
            portfolio.Asset('ass4', issuer=iss[2])
            ])

        p = portfolio.Portfolio('port', asses)

        self.assertEquals(p.assets, asses)
        self.assertSets(p.issuers(), set(iss))
        self.assertSets(p.factors(), set(fs))
        self.assertEquals(p.asset_issuer_map(), dict([
            ('ass1', iss[0]),
            ('ass2', iss[1]),
            ('ass3', iss[2]),
            ('ass4', iss[2])
            ]))

    def test_PortfolioMultiIssuersMultiFactorsDifferentWeights(self):
        fs = [portfolio.Factor('f1', 0.1), portfolio.Factor('f1', 0.2), portfolio.Factor('f3', 0.3)]
        iss = [portfolio.Issuer('iss1', set(fs[0:1])), portfolio.Issuer('iss2', set(fs[1:2])), portfolio.Issuer('iss3', set(fs))]
        asses = set([
            portfolio.Asset('ass1', issuer=iss[0]),
            portfolio.Asset('ass2', issuer=iss[1]),
            portfolio.Asset('ass3', issuer=iss[2]),
            portfolio.Asset('ass4', issuer=iss[2])
            ])

        p = portfolio.Portfolio('port', asses)

        self.assertEquals(p.assets, asses)
        self.assertSets(p.issuers(), set(iss))
        # all we know is that fs[2] is def there but either of fs[0] or fs[1] could have been picked
        # depending on the order of the issuers set and the factors set of those issuers
        actual = p.factors()
        self.assertEquals(len(actual), 2)
        self.assertIn(fs[2], actual)
        self.assertTrue(fs[0] in actual or fs[1] in actual)
        self.assertEquals(p.asset_issuer_map(), dict([
            ('ass1', iss[0]),
            ('ass2', iss[1]),
            ('ass3', iss[2]),
            ('ass4', iss[2])
            ]))

    def test_toElement(self):
        fs = [portfolio.Factor('f1', 0.1), portfolio.Factor('f2', 0.2), portfolio.Factor('f3', 0.3)]
        iss = [portfolio.Issuer('iss1', set(fs[0:1])), portfolio.Issuer('iss2', set(fs[1:2])), portfolio.Issuer('iss3', set(fs))]
        a1 = portfolio.Asset('ass1', issuer=iss[0])
        a2 = portfolio.Asset('ass2', issuer=iss[1])
        a3 = portfolio.Asset('ass3', issuer=iss[2])
        a4 = portfolio.Asset('ass4', issuer=iss[2])

        p = portfolio.Portfolio('port', [a1,a2,a3,a4])
        p_el = p.toElement()

        expected = Element((collabNs, 'portfolio'))
        expected.addElement('name', content='port')
        assets_el = expected.addElement('assets')
        assets_el.addChild(a1.toElement())
        assets_el.addChild(a2.toElement())
        assets_el.addChild(a3.toElement())
        assets_el.addChild(a4.toElement())

        self.assertEquals(p_el.toXml(), expected.toXml())
        self.assertEquals(p_el.uri, collabNs)        
        
    def test_fromElement(self):
        fs = [portfolio.Factor('f1', 0.1), portfolio.Factor('f2', 0.2), portfolio.Factor('f3', 0.3)]
        iss = [portfolio.Issuer('iss1', set(fs[0:1])), portfolio.Issuer('iss2', set(fs[1:2])), portfolio.Issuer('iss3', set(fs))]
        a1 = portfolio.Asset('ass1', issuer=iss[0])
        a2 = portfolio.Asset('ass2', issuer=iss[1])
        a3 = portfolio.Asset('ass3', issuer=iss[2])
        a4 = portfolio.Asset('ass4', issuer=iss[2])

        el = Element((collabNs, 'portfolio'))
        el.addElement('name', content='port')
        assets_el = el.addElement('assets')
        assets_el.addChild(a1.toElement())
        assets_el.addChild(a2.toElement())
        assets_el.addChild(a3.toElement())
        assets_el.addChild(a4.toElement())

        p = portfolio.Portfolio.fromElement(el)
        self.assertEquals(p.name, 'port')
        self.assertEquals(len(p.assets), 4)
        assets = [a1,a2,a3,a4]

        def getExpected(name, assets):
            for a in assets:
                if a.name == name:
                    return a

        for i, ass in enumerate(p.assets):
            expected = getExpected(ass.name, assets)
            self.assertTrue(expected is not None)
            self.assertEquals(ass.dp, expected.dp)
            self.assertEquals(ass.recovery, expected.recovery)
            self.assertEquals(ass.notional, expected.notional)
            iss, exp_iss = ass.issuer, expected.issuer
            self.assertEquals(iss.name, exp_iss.name)
            facs, exp_facs = iss.factors, exp_iss.factors
            self.assertEquals(len(facs), len(exp_facs))

            [checkFactor(f.name, f.weight, exp_facs) for f in facs]

    
    def test_fromElement_noName(self):
        fs = [portfolio.Factor('f1', 0.1), portfolio.Factor('f2', 0.2), portfolio.Factor('f3', 0.3)]
        iss = [portfolio.Issuer('iss1', set(fs[0:1])), portfolio.Issuer('iss2', set(fs[1:2])), portfolio.Issuer('iss3', set(fs))]
        a1 = portfolio.Asset('ass1', issuer=iss[0])
        a2 = portfolio.Asset('ass2', issuer=iss[1])
        a3 = portfolio.Asset('ass3', issuer=iss[2])
        a4 = portfolio.Asset('ass4', issuer=iss[2])

        el = Element((collabNs, 'portfolio'))
        assets_el = el.addElement('assets')
        assets_el.addChild(a1.toElement())
        assets_el.addChild(a2.toElement())
        assets_el.addChild(a3.toElement())
        assets_el.addChild(a4.toElement())

        def doIt():
            p = portfolio.Portfolio.fromElement(el)

        self.assertRaises(portfolio.InvalidPortfolioError, doIt)


    def test_fromElement_noAssets(self):
        el = Element((collabNs, 'portfolio'))
        el.addElement('name', content='port')

        def doIt():
            p = portfolio.Portfolio.fromElement(el)

        self.assertRaises(portfolio.InvalidPortfolioError, doIt)

    def test_fromElement_noAssetsInAssetsElement(self):
        el = Element((collabNs, 'portfolio'))
        el.addElement('name', content='port')
        assets_el = el.addElement('assets')

        p = portfolio.Portfolio.fromElement(el)
        self.assertEquals(p.name, 'port')
        self.assertEquals(p.assets, set())

    def test_fromElement_notTopNode(self):
        el = Element(('http://jabber.org/protocol/pubsub#event', 'item'))
        s = simulation.Parameters(120, 'output', 1000, 'start')
        sim = el.addChild(s.toElement())
        
        fs = [portfolio.Factor('f1', 0.1), portfolio.Factor('f2', 0.2), portfolio.Factor('f3', 0.3)]
        iss = [portfolio.Issuer('iss1', set(fs[0:1])), portfolio.Issuer('iss2', set(fs[1:2])), portfolio.Issuer('iss3', set(fs))]
        a1 = portfolio.Asset('ass1', issuer=iss[0])
        a2 = portfolio.Asset('ass2', issuer=iss[1])
        a3 = portfolio.Asset('ass3', issuer=iss[2])
        a4 = portfolio.Asset('ass4', issuer=iss[2])

        port = sim.addElement('portfolio')
        port.addElement('name', content='port')
        assets_el = port.addElement('assets')
        assets_el.addChild(a1.toElement())
        assets_el.addChild(a2.toElement())
        assets_el.addChild(a3.toElement())
        assets_el.addChild(a4.toElement())

        p = portfolio.Portfolio.fromElement(el)
        self.assertEquals(p.name, 'port')
        self.assertEquals(len(p.assets), 4)
        assets = [a1,a2,a3,a4]

        def getExpected(name, assets):
            for a in assets:
                if a.name == name:
                    return a

        for i, ass in enumerate(p.assets):
            expected = getExpected(ass.name, assets)
            self.assertTrue(expected is not None)
            self.assertEquals(ass.dp, expected.dp)
            self.assertEquals(ass.recovery, expected.recovery)
            self.assertEquals(ass.notional, expected.notional)
            iss, exp_iss = ass.issuer, expected.issuer
            self.assertEquals(iss.name, exp_iss.name)
            facs, exp_facs = iss.factors, exp_iss.factors
            self.assertEquals(len(facs), len(exp_facs))

            [checkFactor(f.name, f.weight, exp_facs) for f in facs]
        
