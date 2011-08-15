# Copyright (c) Simon Parry.
# See LICENSE for details.

"""
Collab: Distributed mathematics using XMPP
"""

# Ensure the user is running the version of python we require.
import sys
if not hasattr(sys, "version_info") or sys.version_info < (2, 6):
    raise RuntimeError("Collab requires Python 2.6 or later.")
del sys

# # setup version
# from collab._version import version
# __version__ = version.short()

#collab constants
COLLAB_HOST = 'collab.coshx' # all components and users and comms are put in this host
ADMIN_JID = "simon@%s" % COLLAB_HOST

COLLAB_NS = "http://coshx.co.uk/protocols/collab/0.1"
PUBSUB_NS = "http://jabber.org/protocol/pubsub"
COMMAND_NS = 'http://jabber.org/protocol/commands'
COMMAND_SET = '/iq[@type="set"]/command[@xmlns="%s"]' % COMMAND_NS

LOGGER_EL = 'logger'
ERROR_EL = 'error'
ID_EL = 'id'
DEFAULTS_EL = 'defaults'

PUBSUB_NODE = "pubsub.%s" % COLLAB_HOST

DEFAULT_BROADCAST_FREQ = 1000
DEFAULT_NUMBER_RUNS = 1000000
DEFAULT_MAX_RUNS = 5000000
DEFAULT_LOAD_BALANCER_FREQ = 5

# AWS stuff
MAIN_HOST = "www.coshx.co.uk" # this points to MAIN_IP
MAIN_IP = '79.125.114.166' # this machine (aws elastic IP) is the xmpp server and is always on
MAIN_PRIVATE_IP = '10.227.113.44' # for internal AWS comms
XMLRPC_URL = 'http://%s:4560' % MAIN_HOST


INFO = {
    'xmpp server': {'port': 10001, 'role': 'xmpp', 'twistd': ''},
    'Collab Manager': {'port': 10002, 'role': 'admin', 'twistd': 'collab_system_manager'},
    'Portfolio manager': {'port': 10003, 'role': 'input', 'twistd': 'collab_portfolios_manager'},
    'Distribution manager': {'port': 10004, 'role': 'output', 'twistd': 'collab_distributions_manager'},
    'Proxy VaR': {'port': 10005, 'role': 'manager', 'twistd': 'collab_proxy_var'},
    'Simulation manager 001': {'port': 10006, 'role': 'worker', 'twistd': 'collab_simulations_manager'},
    # 'Simulation manager 002': {'port': 10007, 'role': 'worker', 'twistd': 'collab_simulations_manager'},
    # 'Simulation manager 003': {'port': 10008, 'role': 'worker', 'twistd': 'collab_simulations_manager'},
    # 'Simulation manager 004': {'port': 10009, 'role': 'worker', 'twistd': 'collab_simulations_manager'},
    # 'Simulation manager 005': {'port': 10010, 'role': 'worker', 'twistd': 'collab_simulations_manager'},
    # 'Portfolio generator': {'port': 10011, 'role': 'input', 'twistd': ''},
    # 'Portfolio sorter': {'port': 10012, 'role': 'output', 'twistd': ''},
    # 'Proxy optimisation': {'port': 10013, 'role': 'manager', 'twistd': ''},
}

def service_name(name):
    return ''.join([ss.lower() for ss in name.split()])


SERVICES = dict(((t['twistd'], service_name(name)) for name, t in INFO.iteritems() if t['twistd'] != ''))

COLLAB_COMPONENTS = ['%s: %s' % (name, t['role']) for name, t in INFO.iteritems()]

