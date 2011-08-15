# Copyright (c) Simon Parry.
# See LICENSE for details.

# support for portfolios and the elements that make them up
from twisted.words.xish import xpath
from twisted.words.xish.domish import Element
from collections import defaultdict

import collab


class PortfolioElementError(Exception):
    pass

class InvalidAssetError(PortfolioElementError):
    pass

DEFAULT_DP = 1.0
DEFAULT_RECOVERY = 1.0
DEFAULT_NOTIONAL = 100.0

class Asset(object):
    """
    The asset class, in a portfolio assets only have one issuer parent, hence a reference held here
    """

    name_qry = xpath.XPathQuery('/asset[@xmlns="%s"]/name' % collab.COLLAB_NS)
    dp_qry = xpath.XPathQuery('/asset[@xmlns="%s"]/dp' % collab.COLLAB_NS)
    recovery_qry = xpath.XPathQuery('/asset[@xmlns="%s"]/recovery' % collab.COLLAB_NS)
    notional_qry = xpath.XPathQuery('/asset[@xmlns="%s"]/notional' % collab.COLLAB_NS)
    issuer_qry = xpath.XPathQuery('/asset[@xmlns="%s"]/issuer' % collab.COLLAB_NS)

    def __init__(self, name, dp=DEFAULT_DP, recovery=DEFAULT_RECOVERY, notional=DEFAULT_NOTIONAL, issuer=None):
        self.name=name
        self.dp=max(min(dp, 1.0), 0.0)
        self.recovery=max(min(recovery, 1.0), 0.0)
        self.notional=notional
        self.issuer = issuer

    def toElement(self):
        el = Element((collab.COLLAB_NS, 'asset'))
        el.addElement('name', content=self.name)
        el.addElement('dp', content=str(self.dp))
        el.addElement('recovery', content=str(self.recovery))
        el.addElement('notional', content=str(self.notional))
        if self.issuer:
            el.addChild(self.issuer.toElement())
        return el

    @staticmethod
    def fromElement(element):
        if not Asset.name_qry.matches(element):
            raise InvalidAssetError('No asset name')

        name = Asset.name_qry.queryForString(element)
        dp, recovery, notional, issuer = DEFAULT_DP, DEFAULT_RECOVERY, DEFAULT_NOTIONAL, None
        if Asset.dp_qry.matches(element):
            dp = float(Asset.dp_qry.queryForString(element))
        if Asset.recovery_qry.matches(element):
            recovery = float(Asset.recovery_qry.queryForString(element))
        if Asset.notional_qry.matches(element):
            notional = float(Asset.notional_qry.queryForString(element))
        if Asset.issuer_qry.matches(element):
            issuer_el = Asset.issuer_qry.queryForNodes(element)[0]
            issuer = Issuer.fromElement(issuer_el)

        return Asset(name, dp, recovery, notional, issuer)
        

class InvalidIssuerError(PortfolioElementError):
    pass

class Issuer(object):
    """
    The issuer class, in a portfolio factors can belong to many issuers, but each issuer has a
    fixed set of factors.
    """
    name_qry = xpath.XPathQuery('/issuer[@xmlns="%s"]/name' % collab.COLLAB_NS)
    factors_qry = xpath.XPathQuery('/issuer[@xmlns="%s"]/factors' % collab.COLLAB_NS)

    def __init__(self, name, factors=None):
        self.name=name
        self.factors = factors or set()

    def toElement(self):
        el = Element((collab.COLLAB_NS, 'issuer'))
        el.addElement('name', content=self.name)
        factors = el.addElement('factors')
        for f in self.factors:
            factors.addChild(f.toElement())
        return el

    @staticmethod
    def fromElement(element):
        if not Issuer.name_qry.matches(element):
            raise InvalidIssuerError('no name')
        if not Issuer.factors_qry.matches(element):
            raise InvalidIssuerError('no factors')

        name = Issuer.name_qry.queryForString(element)

        factors = set()
        for f in Issuer.factors_qry.queryForNodes(element)[0].elements():
            factors.add(Factor.fromElement(f))

        return Issuer(name, factors)


class InvalidFactorError(PortfolioElementError):
    pass

class Factor(object):
    """
    The factor class, name and weight only at the moment
    """
    name_qry = xpath.XPathQuery('/factor[@xmlns="%s"]/name' % collab.COLLAB_NS)
    weight_qry = xpath.XPathQuery('/factor[@xmlns="%s"]/weight' % collab.COLLAB_NS)
    
    def __init__(self, name, weight):
        self.name=name
        self.weight=max(min(weight, 1.0), 0.0)

    def __cmp__(self, other):
        if self.name == other.name:
            return 0

        if self.name < other.name:
            return -1

        if self.name > other.name:
            return 1

    
    def toElement(self):
        el = Element((collab.COLLAB_NS, 'factor'))
        el.addElement('name', content=self.name)
        factors = el.addElement('weight', content=str(self.weight))
        return el

    @staticmethod
    def fromElement(element):
        if not Factor.name_qry.matches(element):
            raise InvalidFactorError('no name')
        if not Factor.weight_qry.matches(element):
            raise InvalidFactorError('no weighting')

        name = Factor.name_qry.queryForString(element)
        weight = float(Factor.weight_qry.queryForString(element))
        return Factor(name, weight)


class InvalidPortfolioError(PortfolioElementError):
    pass

class Portfolio(object):
    """
    The portfolio class, holds assets, issuers and factors via a set of assets
    """
    portfolio_qry = xpath.XPathQuery('//portfolio[@xmlns="%s"]' % collab.COLLAB_NS)
    name_qry = xpath.XPathQuery('/portfolio[@xmlns="%s"]/name' % collab.COLLAB_NS)
    assets_qry = xpath.XPathQuery('/portfolio[@xmlns="%s"]/assets' % collab.COLLAB_NS)
    
    def __init__(self, name, assets=None):
        self.name=name
        self.assets = assets or set()

    def asset_indices(self):
        return dict([(ass.name, i) for i, ass in enumerate(self.assets)])
        
    def issuers(self):
        return set([a.issuer for a in self.assets if a.issuer is not None])

    def issuer_indices(self):
        return dict([(iss.name, i) for i, iss in enumerate(self.issuers())])
    
    def factors(self):
        s=set()
        names = set()
        for a in self.assets:
            if a.issuer is None:
                continue
            for f in a.issuer.factors:
                if f.name not in names:
                    names.add(f.name)
                    s.add(f)
        return s
    
    def all_factors(self):
        s=set()
        for a in self.assets:
            if a.issuer is not None:
                s = s.union(a.issuer.factors)

        return s

    def factor_indices(self):
        return dict([(f.name, i) for i, f in enumerate(self.factors())])

    def defaultProbabilities(self):
        return dict([(a.name, a.dp) for a in self.assets if a.issuer is not None])
    
    def asset_issuer_map(self):
        return dict(
            [(a.name, a.issuer) for a in self.assets if a.issuer is not None]
            )

    def issuer_asset_map(self):
        iamap = defaultdict(list)
        [iamap[a.issuer.name].append(a) for a in self.assets if a.issuer is not None]
        return iamap
        

    def toElement(self):
        el = Element((collab.COLLAB_NS, 'portfolio'))
        el.addElement('name', content=self.name)
        ass_el = el.addElement('assets')
        for a in self.assets:
            ass_el.addChild(a.toElement())
        return el

    @staticmethod
    def fromElement(element):
        if not Portfolio.portfolio_qry.matches(element):
            raise InvalidPortfolioError('Not a portfolio')
        
        el = Portfolio.portfolio_qry.queryForNodes(element)[0]
        if not Portfolio.name_qry.matches(el):
            raise InvalidPortfolioError('no name')
        if not Portfolio.assets_qry.matches(el):
            raise InvalidPortfolioError('no assets')

        name = Portfolio.name_qry.queryForString(el)
        assets = set()
        for asset in Portfolio.assets_qry.queryForNodes(el)[0].elements():
            assets.add(Asset.fromElement(asset))

        return Portfolio(name, assets)

        
def getPortfolio(item, logs):
    try:
        return Portfolio.fromElement(item)
    except PortfolioElementError as e:
        logs.addLog(collab.ERROR_EL, str(e))

        
# def getAssetIssuerMap(portfolio):
#     asset_issuer_map = dict()

#     for a in portfolio.assets:
#         asset_issuer_map[a.name] = a.issuer

#     return asset_issuer_map


# def getFactors(portfolio):
#     factor_weights = []
#     all_issuers_qry = xpath.XPathQuery(PORTFOLIO_QRY+"/issuers/issuer")
#     issuer_id_qry = xpath.XPathQuery("/issuer/id")
#     factor_qry = xpath.XPathQuery("/issuer/factors/factor")
#     name_qry = xpath.XPathQuery("/factor/name")
#     weight_qry = xpath.XPathQuery("/factor/weight")

#     if not all_issuers_qry.matches(portfolio):
#         raise PortfolioParseError('Cannot parse issuers')

#     for iss in all_issuers_qry.queryForNodes(portfolio):
#         if not issuer_id_qry.matches(iss) or not factor_qry.matches(iss):
#             raise PortfolioParseError('Cannot parse factors: %s' % iss)

#         issuer = int(issuer_id_qry.queryForString(iss))
#         for f in factor_qry.queryForNodes(iss):
#             if not name_qry.matches(f) or not weight_qry.matches(f):
#                 raise PortfolioParseError('Cannot parse factor details: %s' % f)

#             factor = name_qry.queryForString(f)
#             weight = float(weight_qry.queryForString(f))
#             factor_weights.append((issuer, factor, weight))

#     return factor_weights


# def getDps(portfolio):
#     dps = dict()
#     assets_qry = xpath.XPathQuery(PORTFOLIO_QRY+"/assets/asset")
#     asset_id_qry = xpath.XPathQuery("/asset/id")
#     dp_qry = xpath.XPathQuery("/asset/default_probability")

#     if not assets_qry.matches(portfolio):
#         raise PortfolioParseError('Cannot parse assets')

#     for a in assets_qry.queryForNodes(portfolio):
#         if not asset_id_qry.matches(a) or not dp_qry.matches(a):
#             raise PortfolioParseError('Cannot parse asset: %s' % a)

#         asset = int(asset_id_qry.queryForString(a))
#         dp = float(dp_qry.queryForString(a))
#         dps[asset] = dp

#     return dps
