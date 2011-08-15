# Copyright (c) Simon Parry.
# See LICENSE for details.

from twisted.internet import defer
from twisted.python import log
from wokkel import data_form
from zope.interface import implements, Interface

import collab
from collab.command import Command, Actions, Note, getCommandElement


def makeExecutingCommand(iq, status='executing'):
    cmd = getCommandElement(iq)
    c = Command(node=cmd['node'], status=status)
    if cmd.hasAttribute('sessionid'):
        c.sessionid = cmd['sessionid']
    return c
    
class CommandPageError(Exception):
    pass

class IPage(Interface):
    def renderToElement(cmd_in, state):
        pass

class CommandPage(object):
    implements(IPage)
    
    def __init__(self, cmd):
        self.cmd = cmd

    def renderToElement(self, cmd_in, state):
        return defer.succeed(self.cmd.toElement())
        

class RegisterMachinePage(object):
    implements(IPage)

    def __init__(self, getRegistered):
        self.getRegistered = getRegistered

    def renderToElement(self, iq, state):
        d_regs = self.getRegistered()
        
        def makeCommand(registered):
            c = makeExecutingCommand(iq)
            a = Actions()
            a.setDefault('complete')
            c.set_actions(a)

            form = data_form.Form(
                formType='form',
                title=u'Register a machine',
                instructions=[
                    'Please give domain name details of the machine',
                    'that needs to be registered with the Collab system'
                    ],
                formNamespace=collab.COLLAB_NS
                )

            form.addField(data_form.Field(
                var = 'machine',
                label = u'Machine',
                desc = u'Please give details of the machine domain name',
                required = True,
                fieldType='text-single'
                ))

            form.addField(data_form.Field(
                var = 'ForExample',
                label = 'For example:',
                fieldType='fixed'
                ))

            for r in registered:
                form.addField(data_form.Field(
                    var = 'registered_%s' %r,
                    label = r,
                    fieldType='fixed'
                    ))
                
            c.set_form(form)
            return c.toElement()

        d_regs.addCallback(makeCommand)
        return d_regs
        
        
class UnregisterMachinePage(object):
    implements(IPage)

    def __init__(self, getRegistered):
        self.getRegistered = getRegistered

    def renderToElement(self, iq, state):
        d_regs = self.getRegistered()

        def makeCommand(registered):
            c = makeExecutingCommand(iq)
            a = Actions()
            a.setDefault('complete')
            c.set_actions(a)

            form = data_form.Form(
                formType='form',
                title=u'Unregister a machine',
                instructions=[u'Please select the machine to be unregistered'],
                formNamespace=collab.COLLAB_NS
                )

            form.addField(data_form.Field(
                var = 'machines',
                label = u'Machines',
                desc = u'Please select the machine domain names to remove',
                required = True,
                fieldType='list-multi',
                options = [data_form.Option(m) for m in registered]
                ))

            c.set_form(form)
            return c.toElement()

        d_regs.addCallback(makeCommand)
        return d_regs

    
class CreateCollabNodePage(object):
    implements(IPage)

    def __init__(self, getRegistered, getComponents):
        self.getRegistered = getRegistered
        self.getComponents = getComponents

    def renderToElement(self, iq, state):
        d_comps = self.getComponents()
        
        def deferredRegistered(components):
            d_regs = self.getRegistered()

            def makeCommand(registered, components):
                c = makeExecutingCommand(iq)
                a = Actions()
                a.setDefault('complete')
                c.set_actions(a)

                form = data_form.Form(
                    formType='form',
                    title=u'Create a Collab Component',
                    instructions=[u'Please select a Collab component to create and a machine to run it on'],
                    formNamespace=collab.COLLAB_NS
                    )

                form.addField(data_form.Field(
                    var = 'component',
                    label = u'Collab component type',
                    desc = u'Please choose the type of Collab component to create',
                    required = True,
                    fieldType='list-single',
                    options = [data_form.Option(o) for o in components]
                    ))

                form.addField(data_form.Field(
                    var = 'machine',
                    label = u'Registered machines',
                    desc = u'Please choose a machine to run the Collab component on',
                    required = True,
                    fieldType='list-single',
                    options = [data_form.Option(m) for m in registered]
                    ))

                c.set_form(form)
                return c.toElement()

            d_regs.addCallback(makeCommand, components)
            return d_regs

        d_comps.addCallback(deferredRegistered)
        return d_comps
    

class CreatePubsubNodePage(object):
    implements(IPage)

    def __init__(self, getComponents):
        self.getComponents = getComponents

    def renderToElement(self, iq, state):
        d_comps = self.getComponents()

        def makeCommand(components):
            c = makeExecutingCommand(iq)
            a = Actions()
            a.setDefault('next')
            a.add('complete')
            c.set_actions(a)

            form = data_form.Form(
                formType='form',
                title=u'Create a communications channel',
                instructions=[u'Please select a Collab component to associate with the channel'
                              , u'and a suggested name for the channel'],
                formNamespace=collab.COLLAB_NS
                )

            form.addField(data_form.Field(
                var = 'component',
                label = u'Collab component type',
                desc = u'Please choose the type of Collab component to associate',
                required = True,
                fieldType='list-single',
                options = [data_form.Option(o) for o in components]
                ))

            form.addField(data_form.Field(
                var = 'name',
                label = u'Suggested name',
                desc = u'Please suggest a name for the channel',
                required = True,
                fieldType='text-single'
                ))

            c.set_form(form)
            return c.toElement()

        d_comps.addCallback(makeCommand)
        return d_comps

class InplaceConfigurePubsubNodePage(object):
    implements(IPage)

    def __init__(self, getPSNodes):
        self.getPSNodes = getPSNodes

    def renderToElement(self, iq, state):
        d_psnodes = self.getPSNodes()

        def makeCommand(discoItems):
            c = makeExecutingCommand(iq)
            a = Actions()
            a.setDefault('next')
            c.set_actions(a)

            form = data_form.Form(
                formType='form',
                title=u'Configure a communications channel',
                instructions=[u'Please choose which communications channel to configure'],
                formNamespace=collab.COLLAB_NS
                )

            form.addField(data_form.Field(
                var = 'name',
                label = u'Available channels',
                desc = u'Please choose the communications channel to configure',
                required = True,
                fieldType='list-single',
                options = [data_form.Option(o.nodeIdentifier) for o in discoItems]
                ))

            c.set_form(form)
            return c.toElement()

        d_psnodes.addCallback(makeCommand)
        return d_psnodes
    
class ConfigurePubsubNodeOwnersPage(object):
    implements(IPage)

    def __init__(self, getAdmins):
        self.getAdmins = getAdmins

    def _getOptions(self, admins):
        return [data_form.Option(o.entity.full()) for o in admins]
    
    def renderToElement(self, iq, state):
        psnode = state['name']
        d_admins = self.getAdmins()

        def makeCommand(admins):
            c = makeExecutingCommand(iq)
            a = Actions()
            a.setDefault('next')
            a.add('prev')
            a.add('complete')
            c.set_actions(a)

            form = data_form.Form(
                formType='form',
                title=u'Configure channel',
                instructions=[u'Set all owners for %s' % psnode],
                formNamespace=collab.COLLAB_NS
                )

            form.addField(data_form.Field(
                var = 'admins',
                label = u'Administrators',
                desc = u'Please choose the owners for %s' % psnode,
                required = True,
                fieldType='list-multi',
                options = self._getOptions(admins)
                ))

            c.set_form(form)
            return c.toElement()

        d_admins.addCallback(makeCommand)
        return d_admins

class ConfigurePubsubNodePublishersPage(object):
    implements(IPage)

    def __init__(self, getPublishers):
        self.getPublishers = getPublishers

    def _getOptions(self, pubs, admins):
        return [data_form.Option(o.entity.full()) for o in pubs if o.entity.full() not in admins]
    
    def renderToElement(self, iq, state):
        psnode = state['name']
        admins = set(state['admins'])
        d_pubs = self.getPublishers()

        def makeCommand(pubs):
            [log.msg(a) for a in pubs]

            c = makeExecutingCommand(iq)
            a = Actions()
            a.setDefault('next')
            a.add('prev')
            a.add('complete')
            c.set_actions(a)

            form = data_form.Form(
                formType='form',
                title=u'Configure channel',
                instructions=[u'Set all input for %s' % psnode],
                formNamespace=collab.COLLAB_NS
                )

            form.addField(data_form.Field(
                var = 'publishers',
                label = u'Publishers',
                desc = u'Please choose who provides the input for %s' % psnode,
                required = True,
                fieldType='list-multi',
                options = self._getOptions(pubs, admins)
                ))

            c.set_form(form)
            return c.toElement()

        d_pubs.addCallback(makeCommand)
        return d_pubs
    
class ConfigurePubsubNodeSubscribersPage(object):
    implements(IPage)

    def __init__(self, getSubscribers):
        self.getSubscribers = getSubscribers

    def _getOptions(self, subs, pubs, admins):
        return [data_form.Option(o.entity.full()) for o in subs if o.entity.full() not in admins.union(pubs)]
        
    def renderToElement(self, iq, state):
        psnode = state['name']
        admins = set(state['admins'])
        pubs = set(state['publishers'])
        d_subs = self.getSubscribers()

        def makeCommand(subs):
            [log.msg(a) for a in subs]

            c = makeExecutingCommand(iq)
            a = Actions()
            a.setDefault('complete')
            a.add('prev')
            c.set_actions(a)

            form = data_form.Form(
                formType='form',
                title=u'Configure channel',
                instructions=[u'Set all output for %s' % psnode],
                formNamespace=collab.COLLAB_NS
                )

            form.addField(data_form.Field(
                var = 'subscribers',
                label = u'Subscribers',
                desc = u'Please choose who receives the output from %s' % psnode,
                required = True,
                fieldType='list-multi',
                options = self._getOptions(subs, pubs, admins)
                ))

            c.set_form(form)
            return c.toElement()

        d_subs.addCallback(makeCommand)
        return d_subs


class DeletePubsubNodePage(object):
    implements(IPage)

    def __init__(self, getPSNodes):
        self.getPSNodes = getPSNodes

    def renderToElement(self, iq, state):
        d_psnodes = self.getPSNodes()

        def makeCommand(discoItems):
            c = makeExecutingCommand(iq)
            a = Actions()
            a.setDefault('complete')
            c.set_actions(a)

            form = data_form.Form(
                formType='form',
                title=u'Delete communications channels',
                instructions=[u'Please select the channel to delete'],
                formNamespace=collab.COLLAB_NS
                )

            form.addField(data_form.Field(
                var = 'name',
                label = u'Channel name',
                desc = u'Please choose the channel to delete',
                required = True,
                fieldType='list-multi',
                options=[data_form.Option(o.nodeIdentifier) for o in discoItems]
                ))

            c.set_form(form)
            return c.toElement()

        d_psnodes.addCallback(makeCommand)
        return d_psnodes

    
class EndPage(object):
    implements(IPage)

    def __init__(self, msg):
        self.msg = msg

    def renderToElement(self, iq, state):
        c = makeExecutingCommand(iq, 'completed')
        n = Note(self.msg, note_type='info')
        c.addNote(n)
        
        return defer.succeed(c.toElement())


class ViewCollabChannelsPage(object):
    implements(IPage)

    def __init__(self, jid, inputNode, outputNode, errorNode):
        self.jid = jid
        self.inputNode = inputNode
        self.outputNode = outputNode
        self.errorNode = errorNode

    def renderToElement(self, iq, state):
        d_inputs = self.inputNode.inputChannels()
        
        def getOutputs(inputs):
            d_outputs = self.outputNode.outputChannels()

            def getErrors(outputs, inputs):
                d_errors = self.errorNode.errorChannels()

                def makeCommand(errors, outputs, inputs):
                    c = makeExecutingCommand(iq)
                    a = Actions()
                    a.setDefault('complete')
                    c.set_actions(a)

                    form = data_form.Form(
                        formType='form',
                        title=u'Input, output and error channels for %s' % self.jid.full(),
                        formNamespace=collab.COLLAB_NS
                        )

                    form.addField(data_form.Field(
                        var = 'input_channels',
                        label = u'Input channels',
                        required = False,
                        fieldType='text-multi',
                        values = inputs
                        ))

                    form.addField(data_form.Field(
                        var = 'output_channels',
                        label = u'Output channels',
                        required = False,
                        fieldType='text-multi',
                        values = outputs
                        ))

                    form.addField(data_form.Field(
                        var = 'error_channels',
                        label = u'Error channels',
                        required = False,
                        fieldType='text-multi',
                        values = errors
                        ))

                    c.set_form(form)
                    return c.toElement()

                d_errors.addCallback(makeCommand, outputs, inputs)
                return d_errors

            d_outputs.addCallback(getErrors, inputs)
            return d_outputs

        d_inputs.addCallback(getOutputs)
        return d_inputs

    
class ConfigureCollabNodeLoadBalancerPage(object):
    implements(IPage)

    def renderToElement(self, iq, state):
        c = makeExecutingCommand(iq)
        a = Actions()
        a.setDefault('complete')
        c.set_actions(a)

        form = data_form.Form(
            formType='form',
            title=u'Configure the load balancing',
            instructions=[u'Please set the frequency (per second) for checking the load.'],
            formNamespace=collab.COLLAB_NS
            )

        form.addField(data_form.Field(
            var = 'frequency',
            label = u'Frequency',
            desc = u'Please set the desired frequency per second',
            required = True,
            fieldType='text-single'
            ))

        c.set_form(form)
        return defer.succeed(c.toElement())


class LHPPortfolioPage(object):
    implements(IPage)

    def renderToElement(self, iq, state):
        c = makeExecutingCommand(iq)
        a = Actions()
        a.setDefault('complete')
        c.set_actions(a)

        form = data_form.Form(
            formType='form',
            title=u'Configure the portfolio',
            instructions=[u'Please choose the parameters of a large homogeneous portfolio.'],
            formNamespace=collab.COLLAB_NS
            )

        form.addField(data_form.Field(
            var = 'default_probability',
            label = u'Default Probability',
            desc = u'Please set the uniform asset default probability',
            required = True,
            fieldType='text-single'
            ))
        
        form.addField(data_form.Field(
            var = 'base_correlation',
            label = u'Base Correlation',
            desc = u'Please set the portfolio base correlation',
            required = True,
            fieldType='text-single'
            ))
        
        form.addField(data_form.Field(
            var = 'number_issuers',
            label = u'Number of Issuers',
            desc = u'Please set the number of defaultible issuers in the portfolio',
            required = True,
            fieldType='text-single'
            ))
        
        form.addField(data_form.Field(
            var = 'number_runs',
            label = u'Number of runs',
            desc = u'Please set the minimum number of runs to perform',
            required = True,
            fieldType='text-single'
            ))

        c.set_form(form)
        return defer.succeed(c.toElement())

class ClientRegisterPage(object):
    implements(IPage)

    def renderToElement(self, iq, state):
        c = makeExecutingCommand(iq)
        a = Actions()
        a.setDefault('complete')
        c.set_actions(a)

        form = data_form.Form(
            formType='form',
            title=u'Register a client',
            instructions=[u'Please choose which client to register.'],
            formNamespace=collab.COLLAB_NS
            )

        form.addField(data_form.Field(
            var = 'client_jid',
            label = u'Client identifier',
            desc = u'Please choose which client',
            required = True,
            fieldType='text-single'
            ))
        
        c.set_form(form)
        return defer.succeed(c.toElement())

class ClientUnregisterPage(object):
    implements(IPage)

    def renderToElement(self, iq, state):
        c = makeExecutingCommand(iq)
        a = Actions()
        a.setDefault('complete')
        c.set_actions(a)

        form = data_form.Form(
            formType='form',
            title=u'Unregister a client',
            instructions=[u'Please choose which client to unregister.'],
            formNamespace=collab.COLLAB_NS
            )

        form.addField(data_form.Field(
            var = 'client_jid',
            label = u'Client identifier',
            desc = u'Please choose which client',
            required = True,
            fieldType='text-single'
            ))
        
        c.set_form(form)
        return defer.succeed(c.toElement())
