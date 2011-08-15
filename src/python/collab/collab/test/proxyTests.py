# Copyright (c) Simon Parry.
# See LICENSE for details.

from twisted.trial import unittest


class CollabProxyTests(unittest.TestCase):
    """
    CollabProxyTests: Tests for the Public API Proxy for VaR calculations

    Want the API to have two way communication between clients and itself
    Want it to accept a two-way comms channel
    Want it to kick off simulations
    Broadcast progress
    Broadcast results
    """
    
    timeout = 2
    
    def setUp(self):
    	pass
    
    def tearDown(self):
    	pass
    
    def test_something(self):
        pass
