# Copyright (c) Simon Parry.
# See LICENSE for details.

from collections import defaultdict

import numpy as np
from mock import Mock
from scipy.stats import norm
from twisted.trial import unittest

from collab import portfolio as port
from collab.copulas import PysparseGaussianCopula


def lhp(corr, dp, percentile):
    corr1 = np.sqrt(max(1.0-corr, 0.0))
    corr2 = np.sqrt(max(corr, 0.0))
    inv_percentile = norm.ppf(percentile)
    inv_dp = norm.ppf(dp)
    inter = (corr2 * inv_percentile + inv_dp)/corr1
    return norm.cdf(inter)
    
def percentile_hist(hist, perc):
    if perc <= 0:
        return 0

    num_elements = sum(hist)
    index = int(np.ceil(perc*(num_elements-1)))
    limit = min(index, num_elements-1)
    if limit <= 0:
        return 0
    
    total = 0
    for i, h in enumerate(hist):
        total += h
        if total >= limit:
            return float(min(i+1, num_elements))/len(hist)

    return float(num_elements)/len(hist)
    
def makePortfolio(corr, dp, n):
    f = port.Factor('factor', corr)
    assets = set()
    for a in xrange(n-1):
        iss = port.Issuer('issuer%s' % a, set([f]))
        assets.add(port.Asset('asset%s' % a, dp, issuer=iss))

    return port.Portfolio('portfolio', assets)

class GaussianCopulaTests(unittest.TestCase):
    """
    GaussianCopulaTests: Tests for the L{PysparseGaussianCopula} class

    test the logic plus

    one factor LHP approx:
        P(L<x) ~ norm((sqrt(1-corr) * inv_norm(x) - inv_norm(dp))/sqrt(corr))

    2-factor FFT, binomial?

    
    
    """
    
#    timeout = 2
    
    def setUp(self):
        self.f1 = port.Factor('f1', 0.1)
        self.f2 = port.Factor('f2', 0.2)
        self.iss1 = port.Issuer('iss1', set([self.f1]))
        self.iss2 = port.Issuer('iss2', set([self.f2]))
        self.iss3 = port.Issuer('iss3', set([self.f1, self.f2]))
        self.ass1 = port.Asset('ass1', dp=0.1, recovery=0.9, notional=100.0, issuer=self.iss1)
        self.ass2 = port.Asset('ass2', dp=0.2, recovery=0.9, notional=200.0, issuer=self.iss2)
        self.ass3 = port.Asset('ass3', dp=0.3, recovery=0.9, notional=300.0, issuer=self.iss3)
        self.ass4 = port.Asset('ass4', dp=0.4, recovery=0.9, notional=400.0, issuer=self.iss1)
        assets = set([self.ass1, self.ass2, self.ass3, self.ass4])
        self.p =  port.Portfolio('p1', assets)
    
    def tearDown(self):
    	pass
    
    def test_init(self):
        p = port.Portfolio('jim')
        copula = PysparseGaussianCopula(p)
        self.assertTrue(copula is not None)
        
    def test_init_assetsIssuers(self):

        gc = PysparseGaussianCopula(self.p)

        self.assertEquals(len(gc.issuers), 3)
        self.assertTrue(self.iss1 in gc.issuers)
        self.assertTrue(self.iss2 in gc.issuers)
        self.assertTrue(self.iss3 in gc.issuers)
        self.assertEquals(len(gc.assets), 4)
        self.assertTrue(self.ass1 in gc.assets)
        self.assertTrue(self.ass2 in gc.assets)
        self.assertTrue(self.ass3 in gc.assets)
        self.assertTrue(self.ass4 in gc.assets)
        
    def test_init_assetsIssuersMap(self):

        gc = PysparseGaussianCopula(self.p)

        mp =  gc.asset_issuer_map
        issuers = gc.issuers
        for i, a in enumerate(gc.assets):
            self.assertEquals(a.issuer, issuers[int(mp[i])])
        
    def test_init_thresholds(self):

        gc = PysparseGaussianCopula(self.p)

        thrs = gc.thresholds
        for i, a in enumerate(gc.assets):
            self.assertEquals(norm.ppf(a.dp), thrs[i])
        
    def test_init_sizes(self):

        gc = PysparseGaussianCopula(self.p)

        self.assertEquals(3, gc.n_issuers)
        self.assertEquals(4, gc.n_assets)
        self.assertEquals(2, gc.n_factors)
        
    def test_init_weightsMatrix_sizes(self):

        gc = PysparseGaussianCopula(self.p)

        wm = gc.weights
        # number issuers
        self.assertEquals(3, np.size(wm, 0))
        # number factors + number issuers
        self.assertEquals(5, np.size(wm, 1))
        
    def assertArray(self, a1, a2):
        self.assertEquals(len(a1), len(a2))
        for i in xrange(len(a1)):
            self.assertAlmostEqual(a1[i], a2[i], 6)

    def test_init_weightsMatrix_allWeights(self):

        factor_indices = dict({'f1':0, 'f2':1})
        self.p.factor_indices = Mock(return_value=factor_indices)
        self.p.issuers = Mock(return_value=[self.iss1, self.iss2, self.iss3])
        gc = PysparseGaussianCopula(self.p)

        expected = np.zeros(shape=(3, 5))
        expected[:,0] = [np.sqrt(self.f1.weight), 0.0, np.sqrt(self.f1.weight)]
        expected[:,1] = [0.0, np.sqrt(self.f2.weight), np.sqrt(self.f2.weight)]
        expected[:,2] = [np.sqrt(1.0 - self.f1.weight), 0.0, 0.0]
        expected[:,3] = [0.0, np.sqrt(1.0 - self.f2.weight), 0.0]
        expected[:,4] = [0.0, 0.0, np.sqrt(1.0 - self.f1.weight - self.f2.weight)]

        wm = gc.weights
        for i in xrange(5):
            unit = np.zeros(5)
            unit[i] = 1.0
            arr = np.empty(3)
            wm.matvec(unit, arr)
            self.assertArray(arr, expected[:, i])

    def test_init_weightsMatrix_differentExposures(self):
        f1 = port.Factor('f1', 0.1)
        f2 = port.Factor('f2', 0.2)
        f3 = port.Factor('f1', 0.3) # different exposure to the same factor
        iss1 = port.Issuer('iss1', set([f1]))
        iss2 = port.Issuer('iss2', set([f2]))
        iss3 = port.Issuer('iss3', set([f3, f2]))
        ass1 = port.Asset('ass1', dp=0.1, recovery=0.9, notional=100.0, issuer=iss1)
        ass2 = port.Asset('ass2', dp=0.2, recovery=0.9, notional=200.0, issuer=iss2)
        ass3 = port.Asset('ass3', dp=0.3, recovery=0.9, notional=300.0, issuer=iss3)
        ass4 = port.Asset('ass4', dp=0.4, recovery=0.9, notional=400.0, issuer=iss1)
        assets = set([ass1, ass2, ass3, ass4])
        p =  port.Portfolio('p1', assets)

        factor_indices = dict({'f1':0, 'f2':1})
        p.factor_indices = Mock(return_value=factor_indices)
        p.issuers = Mock(return_value=[iss1, iss2, iss3])
        gc = PysparseGaussianCopula(p)

        expected = np.zeros(shape=(3, 5))
        expected[:,0] = [np.sqrt(f1.weight), 0.0, np.sqrt(f3.weight)]
        expected[:,1] = [0.0, np.sqrt(f2.weight), np.sqrt(f2.weight)]
        expected[:,2] = [np.sqrt(1.0 - f1.weight), 0.0, 0.0]
        expected[:,3] = [0.0, np.sqrt(1.0 - f2.weight), 0.0]
        expected[:,4] = [0.0, 0.0, np.sqrt(1.0 - f3.weight - f2.weight)]

        wm = gc.weights
        for i in xrange(5):
            unit = np.zeros(5)
            unit[i] = 1.0
            arr = np.empty(3)
            wm.matvec(unit, arr)
            self.assertArray(arr, expected[:, i])

    def test_copula_basic(self):

        gc = PysparseGaussianCopula(self.p)

        gc.weights = Mock()
        gc.weights.matvec = Mock()
        gc.defaultProcessor = Mock()

        defaults = defaultdict(int)
        gc.copula(100, 10, defaults)
        self.assertEquals(gc.weights.matvec.call_count, 10*100)
        self.assertEquals(gc.defaultProcessor.call_count, 10)
            

    def test_defaultProcessor_firstIssuerDefaultsAllTheTime(self):

        gc = PysparseGaussianCopula(self.p)
        # need to make sure because of issuer set
        gc.asset_issuer_map = [0,1,2,0]

        gc.thresholds = np.zeros(4)
        num_runs = 10
        corrValues = np.zeros(shape=(3, num_runs))
        corrValues[0, :] -= 1.0 # issuer 0 will default all the time

        defaults = defaultdict(int)
        gc.defaultProcessor(defaults, corrValues)
        self.assertEquals(defaults[0], 0)
        self.assertEquals(defaults[1], 0)
        self.assertEquals(defaults[2], 10) # two assets are linked to issuer 0
        self.assertEquals(defaults[3], 0)
        self.assertEquals(defaults[4], 0)

    def test_defaultProcessor_firstIssuerDefaultsNotAllTheTime(self):

        gc = PysparseGaussianCopula(self.p)
        # need to make sure because of issuer set
        gc.asset_issuer_map = [0,1,2,0]

        gc.thresholds = np.zeros(4)
        num_runs = 10
        corrValues = np.zeros(shape=(3, num_runs))
        corrValues[0, :] = np.linspace(-5.0, 4.0, num_runs)

        defaults = defaultdict(int)
        gc.defaultProcessor(defaults, corrValues)
        self.assertEquals(defaults[0], 5)
        self.assertEquals(defaults[1], 0)
        self.assertEquals(defaults[2], 5) # two assets are linked to issuer 0
        self.assertEquals(defaults[3], 0)
        self.assertEquals(defaults[4], 0)

    def test_defaultProcessor_secondIssuerDefaultsAllTheTime(self):

        gc = PysparseGaussianCopula(self.p)
        # need to make sure because of issuer set
        gc.asset_issuer_map = [0,1,2,0]

        gc.thresholds = np.zeros(4)
        num_runs = 10
        corrValues = np.zeros(shape=(3, num_runs))
        corrValues[1, :] -= 1.0 # issuer 1 will default all the time

        defaults = defaultdict(int)
        gc.defaultProcessor(defaults, corrValues)
        self.assertEquals(defaults[0], 0)
        self.assertEquals(defaults[1], 10)
        self.assertEquals(defaults[2], 0)
        self.assertEquals(defaults[3], 0)
        self.assertEquals(defaults[4], 0)

    def test_defaultProcessor_thirdIssuerDefaultsAllTheTime(self):

        gc = PysparseGaussianCopula(self.p)
        # need to make sure because of issuer set
        gc.asset_issuer_map = [0,1,2,0]

        gc.thresholds = np.zeros(4)
        num_runs = 10
        corrValues = np.zeros(shape=(3, num_runs))
        corrValues[2, :] -= 1.0 # issuer 1 will default all the time

        defaults = defaultdict(int)
        gc.defaultProcessor(defaults, corrValues)
        self.assertEquals(defaults[0], 0)
        self.assertEquals(defaults[1], 10)
        self.assertEquals(defaults[2], 0)
        self.assertEquals(defaults[3], 0)
        self.assertEquals(defaults[4], 0)

    def test_defaultProcessor_noDefaults(self):

        gc = PysparseGaussianCopula(self.p)

        gc.thresholds = np.zeros(4)
        gc.thresholds -= 100.0
        num_runs = 10
        corrValues = np.zeros(shape=(3, num_runs))

        defaults = defaultdict(int)
        gc.defaultProcessor(defaults, corrValues)
        self.assertEquals(defaults[0], 10)
        self.assertEquals(defaults[1], 0)
        self.assertEquals(defaults[2], 0)
        self.assertEquals(defaults[3], 0)
        self.assertEquals(defaults[4], 0)

    def test_defaultProcessor_allDefaults(self):

        gc = PysparseGaussianCopula(self.p)

        gc.thresholds = np.zeros(4)
        gc.thresholds += 100.0
        num_runs = 10
        corrValues = np.zeros(shape=(3, num_runs))

        defaults = defaultdict(int)
        gc.defaultProcessor(defaults, corrValues)
        self.assertEquals(defaults[0], 0)
        self.assertEquals(defaults[1], 0)
        self.assertEquals(defaults[2], 0)
        self.assertEquals(defaults[3], 0)
        self.assertEquals(defaults[4], 10)
        
            

                
                


    # def test_largeHomogeneousPortfolio(self):
    #     corrs = [0.3]#, 0.05]
    #     dps = [0.05]#, 0.02]
    #     percentiles = [0.99]

    #     expected = {}
    #     for corr in corrs:
    #         for dp in dps:
    #             for p in percentiles:
    #                 expected = lhp(corr, dp, p)

    #                 size = 5000
    #                 port = makePortfolio(corr, dp, size)
    #                 defaults = np.zeros(size, int)
    #                 PysparseGaussianCopula(port).copula(1000, 100, defaults)
    #                 actual = percentile_hist(defaults, p)
    #                 self.assertAlmostEquals(actual, expected, places=2)
