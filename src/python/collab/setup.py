# setup info for Collab 
from distutils.core import setup
setup(
    name = "collab",
    packages = [
        "collab",
        "collab.test",
        "collab.tapfiles",
        "collab.tapfiles.collabProxyVar",
        "collab.tapfiles.collabSystemManager",
        "collab.tapfiles.correlatedDefaultsManager",
        "collab.tapfiles.correlatedDefaultsSimulator",
        "collab.tapfiles.distributionsManager",
        "twisted.plugins",
        ],
    version = "0.1.0",
    description = "A distributed mathematics framework based on XMPP",
    author = "Simon Parry",
    author_email = "simon.parry@coshx.co.uk",
    url = "https://github.com/wyn/collab",
    download_url = "https://github.com/wyn/collab",
    keywords = ["mathematics", "twisted", "xmpp", "wokkel"],
    classifiers = [
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.6",
        "Development Status :: 2 - Pre-alpha",
        "Environment :: Other Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Mathematics",
        ],
    long_description = """\
An XMPP-based, distributed mathematics framework
-----------------------------------------------

An experimental framework for exploring the building of distributed mathematics
systems using the Extensible Messaging and Presence Protocol (XMPP).

As a first attempt the multi-factor Gaussian copula simulation of a portfolio of
defaultable assets has been implemented.

This version requires Python 2.6 or later.

"""
)
