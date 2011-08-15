# Copyright (c) Simon Parry.
# See LICENSE for details.

from zope.interface import implements, Interface

class IInputNode(Interface):
    """
    Interface for Collab nodes that receive input from multiple channels
    """

    def inputChannels():
        """
        Returns a list of the currently set input channels
        """

    def addInput(input_ch):
        """
        Adds a new input_ch channel
        """

    def removeInput(input_ch):
        """
        removes the given input_ch channel
        """

    def canProcessInputSchema(schema):
        """
        Returns whether this can process the given schema
        """

class IOutputNode(Interface):
    """
    Interface for Collab nodes that send output to a single channel
    """
    
    def outputChannels():
        """
        Returns the one output channel this thing writes to
        """

    def outputSchema():
        """
        Returns some sort of description of the types of output produced
        """

    def onOutput(data):
        """
        Called when there is output to send
        """
    
class IErrorNode(Interface):
    """
    Interface for nodes that can write to some error output
    """

    def errorChannels():
        """
        Returns the one output channel this thing writes to
        """

    def onError(error):
        """
        Called when an error occurs
        """

class ILoadBalancer(Interface):
    """
    Interface for components that can manage their own load levels
    """

    def overloaded(environment):
        """
        Given the environment returns whether its overloaded or not
        """

    def suspendAll(input_node):
        """
        Suspends all input, returns the input channels suspended
        """

    def reloadAll(input_node, old_inputs):
        """
        Reload all input
        """
