# Copyright (c) Simon Parry.
# See LICENSE for details.

import numpy as np
from scipy.stats import norm
from twisted.python import log
from zope.interface import implements, Interface


def makeAssetIssuerIndexMap(issuers, assets):
    issmap = dict((iss.name, i) for i, iss in enumerate(issuers))
    d = np.empty(shape=len(assets))
    for i, ass in enumerate(assets):
        index = issmap[ass.issuer.name]
        d[i] = index

    return d

theSimulatorFactory = {}

class ICopula(Interface):

    def copula(chunk, number_chunks, defaults):
        pass

class PysparseGaussianCopula(object):
    """
    Gaussian copula simulation of correlated defaults
    """
    implements(ICopula)

    def __init__(self, portfolio):
        from pysparse.sparse import spmatrix
        # set up sparse matrices
        # these first two lists define all indices for asset and issuer arrays
        self.issuers = [i for i in portfolio.issuers()]
        self.assets = [a for a in portfolio.assets]
        self.asset_issuer_map = makeAssetIssuerIndexMap(self.issuers, self.assets)

        def ppfGen(assets):
            for ass in assets:
                yield norm.ppf(ass.dp)

        self.thresholds = np.fromiter(ppfGen(self.assets), np.double)

        self.n_issuers = len(self.issuers)
        self.n_assets = len(self.assets)
        factor_indices = portfolio.factor_indices() # on class for testing help
        self.n_factors = len(factor_indices.keys())
        
        #do the factor weights, also running sum for ideosyncratic weights
        wm = spmatrix.ll_mat(self.n_issuers, self.n_factors+self.n_issuers)
        for i, iss in enumerate(self.issuers):
            wsum = 0.0
            for f in iss.factors:
                j = factor_indices[f.name]
                w = np.sqrt(max(f.weight, 0.0))
                wm[i, j] = w
                wsum += w*w
            wm[i, self.n_factors+i] = np.sqrt(max(1.0 - wsum, 0.0))
            
        self.weights = wm.to_csr()
        
    def copula(self, chunk, number_chunks, defaults):
        n = self.n_factors+self.n_issuers
        for outer in xrange(number_chunks):
            # do a chunk
            # corrValues matrix will get filled with correlated randoms in the inner loop
            corrValues = np.empty(shape=(self.n_issuers, chunk), dtype=np.double)
            uncorrValues = norm.rvs(size=(n, chunk))
            for inner in xrange(chunk):
                # take a view of the column we want, column has length issuers
                corr = corrValues[:,inner]
                # make a vector of n randoms
                variates = uncorrValues[:,inner]

                # issuers x (factors+issuers) * (factors+issuers) x 1 = issuers x 1
                # but this result is put into the corr column of corrvalues which is issuers x chunk
                self.weights.matvec(variates, corr)

            self.defaultProcessor(defaults, corrValues)
            log.msg('progress: [ %s/%s ]' % (outer*chunk, chunk*number_chunks))

    def defaultProcessor(self, defaults, corrValues):
        #count how many defaulted and add a tally to that histogram point
        num_runs = np.size(corrValues, 1)
        raw_data = np.empty(shape=(self.n_assets, num_runs), dtype=np.double)
        for i in xrange(self.n_assets):
            issuer_index = self.asset_issuer_map[i]
            raw_data[i, :] = corrValues[issuer_index, :] < self.thresholds[i]

        for i in xrange(num_runs):
            num_defaults = int(sum(raw_data[:,i]))
            defaults[num_defaults] += 1

theSimulatorFactory['sparse'] = PysparseGaussianCopula


class ScipyGaussianCopula(object):
    """
    Gaussian copula simulation of correlated defaults using scipy sparse matrix lib
    """
    implements(ICopula)

    def __init__(self, portfolio):
        from scipy import sparse
        # set up sparse matrices
        # these first two lists define all indices for asset and issuer arrays
        self.issuers = [i for i in portfolio.issuers()]
        self.assets = [a for a in portfolio.assets]
        self.asset_issuer_map = makeAssetIssuerIndexMap(self.issuers, self.assets)

        def ppfGen(assets):
            for ass in assets:
                yield norm.ppf(ass.dp)

        self.thresholds = np.fromiter(ppfGen(self.assets), np.double)

        self.n_issuers = len(self.issuers)
        self.n_assets = len(self.assets)
        factor_indices = portfolio.factor_indices() # on class for testing help
        self.n_factors = len(factor_indices.keys())
        
        #do the factor weights, also running sum for ideosyncratic weights
        wm = sparse.dok_matrix((self.n_issuers, self.n_factors+self.n_issuers), dtype=np.float32)
        for i, iss in enumerate(self.issuers):
            wsum = 0.0
            for f in iss.factors:
                j = factor_indices[f.name]
                w = np.sqrt(max(f.weight, 0.0))
                wm[i, j] = w
                wsum += w*w
            wm[i, self.n_factors+i] = np.sqrt(max(1.0 - wsum, 0.0))
            
        self.weights = wm.tocsr()
        
    def copula(self, chunk, number_chunks, defaults):
        n = self.n_factors+self.n_issuers
        for outer in xrange(number_chunks):
            # do a chunk
            # corrValues matrix will get filled with correlated randoms in the inner loop
            corrValues = np.empty(shape=(self.n_issuers, chunk), dtype=np.double)
            uncorrValues = norm.rvs(size=(n, chunk))
            for inner in xrange(chunk):
                # take a view of the column we want, column has length issuers
                corr = corrValues[:,inner]
                # make a vector of n randoms
                variates = uncorrValues[:,inner]

                # issuers x (factors+issuers) * (factors+issuers) x 1 = issuers x 1
                # but this result is put into the corr column of corrvalues which is issuers x chunk
                self.weights.matvec(variates, corr)

            self.defaultProcessor(defaults, corrValues)
            log.msg('progress: [ %s/%s ]' % (outer*chunk, chunk*number_chunks))

    def defaultProcessor(self, defaults, corrValues):
        #count how many defaulted and add a tally to that histogram point
        num_runs = np.size(corrValues, 1)
        raw_data = np.empty(shape=(self.n_assets, num_runs), dtype=np.double)
        for i in xrange(self.n_assets):
            issuer_index = self.asset_issuer_map[i]
            raw_data[i, :] = corrValues[issuer_index, :] < self.thresholds[i]

        for i in xrange(num_runs):
            num_defaults = int(sum(raw_data[:,i]))
            defaults[num_defaults] += 1

theSimulatorFactory['scipy'] = ScipyGaussianCopula
