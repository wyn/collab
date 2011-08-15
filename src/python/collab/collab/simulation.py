# Copyright (c) Simon Parry.
# See LICENSE for details.

from collections import defaultdict
from datetime import datetime

from twisted.words.xish import xpath
from twisted.words.xish.domish import Element

import collab


class SimulationElementError(Exception):
    pass

class InvalidParametersError(SimulationElementError):
    pass

DEFAULT_RUN_ID = '0'
DEFAULT_OUTPUT = ''
DEFAULT_NUMBER_RUNS = 1000000
DEFAULT_CMD = 'info'


class Parameters(object):

    cmds = set(['info', 'start', 'stop', 'results'])

    parameters_qrystr = 'simulation[@xmlns="%s"]/parameters' % collab.COLLAB_NS
    parameters_qry = xpath.XPathQuery('//%s' % parameters_qrystr)
    run_id_qry = xpath.XPathQuery('/%s/run_id' % parameters_qrystr)
    output_qry = xpath.XPathQuery('/%s/output' % parameters_qrystr)
    number_runs_qry = xpath.XPathQuery('/%s/number_runs' % parameters_qrystr)
    cmd_qry = xpath.XPathQuery('/%s/command' % parameters_qrystr)
    timestamp_qry = xpath.XPathQuery('/%s/timestamp' % parameters_qrystr)
    
    def __init__(self, run_id=DEFAULT_RUN_ID, output=DEFAULT_OUTPUT, number_runs=DEFAULT_NUMBER_RUNS, cmd=DEFAULT_CMD, timestamp=None):
        if cmd not in Parameters.cmds:
            raise InvalidParametersError('Invalid command %s' % cmd)
        self.run_id = run_id
        self.output = output
        self.number_runs = abs(number_runs)
        self.cmd = cmd
        self.timestamp = timestamp or datetime.now()

    def setCommand(self, cmd):
        if cmd not in Parameters.cmds:
            raise InvalidParametersError('Invalid command %s' % cmd)
        self.cmd = cmd

    def toElement(self):
        el = Element((collab.COLLAB_NS, 'simulation'))
        params = el.addElement('parameters')
        params.addElement('run_id', content=str(self.run_id))
        params.addElement('output', content=self.output)
        params.addElement('number_runs', content=str(self.number_runs))
        params.addElement('command', content=self.cmd)
        params.addElement('timestamp', content=str(self.timestamp))
        return el

    @staticmethod
    def fromElement(element):
        if not Parameters.parameters_qry.matches(element):
            raise InvalidParametersError('Cannot find parameters')
        run_id, output, number_runs, cmd, timestamp = DEFAULT_RUN_ID, DEFAULT_OUTPUT, DEFAULT_NUMBER_RUNS, DEFAULT_CMD, None

        el = Parameters.parameters_qry.queryForNodes(element)[0]
        if Parameters.run_id_qry.matches(el):
            run_id = Parameters.run_id_qry.queryForString(el)
        if Parameters.output_qry.matches(el):
            output = Parameters.output_qry.queryForString(el)
        if Parameters.number_runs_qry.matches(el):
            number_runs = int(Parameters.number_runs_qry.queryForString(el))
        if Parameters.cmd_qry.matches(el):
            cmd = Parameters.cmd_qry.queryForString(el)
        if Parameters.timestamp_qry.matches(el):
            timestamp = datetime.strptime(
                Parameters.timestamp_qry.queryForString(el),
                '%Y-%m-%d %H:%M:%S.%f'
                )

        return Parameters(run_id, output, number_runs, cmd, timestamp)



class InvalidDistributionsError(SimulationElementError):
    pass
        

class Distributions(object):
    """
    Distributions: Provides domish support for distributions data
    
    @ivar histograms: a map of named distribution data
    @type histograms: C{dict} of C{string} to L{defaultdict}
    
    """

    dist_qry = xpath.XPathQuery('//distributions[@xmlns="%s"]' % collab.COLLAB_NS)
    hist_qry = xpath.XPathQuery('/distributions[@xmlns="%s"]/histogram' % collab.COLLAB_NS)
    
    def __init__(self, histograms=None):
        self.histograms = histograms or {}

    def combine(self, name, dist):
        if name not in self.histograms:
            self.histograms[name] = defaultdict(int)
        h = self.histograms[name]
        for pt, val in dist.items():
            h[pt] += val

    def toElement(self):
        """
        toElement: converts to a L{Element}

        @rtype: L{Element}
        
        """
        el = Element((collab.COLLAB_NS, 'distributions'))
        for nm, histogram in self.histograms.iteritems():
            hist = el.addElement('histogram')
            hist['name'] = str(nm)
            for pt, val in histogram.iteritems():
                data_el = hist.addElement('data')
                data_el['point'] = str(pt)
                data_el['value'] = str(val)

        return el

    @staticmethod
    def fromElement(element):
        """
        fromElement: Parses the given domish element back to object form
        
        @param element: the element to parse
        @type element:  L{Element}
        
        @rtype: L{Distributions}
        
        """
        if not Distributions.dist_qry.matches(element):
            raise InvalidDistributionsError('No distributions found')

        histograms = {}
        el = Distributions.dist_qry.queryForNodes(element)[0]
        if not Distributions.hist_qry.matches(el):
            return Distributions()
        for hist_el in Distributions.hist_qry.queryForNodes(el):
            name = hist_el.getAttribute('name')
            if not name:
                raise InvalidDistributionsError('Distribution has no name')

            if not name in histograms:
                histograms[name] = defaultdict(int)
            hist = histograms[name]

            for data in hist_el.elements():
                if data.name != 'data':
                    continue
                try:
                    point, value = int(data['point']), int(data['value'])
                    hist[point] += value
                except KeyError as e:
                    raise InvalidDistributionsError('Bad data structure: %s' % e)
                except ValueError as e:
                    raise InvalidDistributionsError('Bad data: %s' % e)

        return Distributions(histograms)
                
class InvalidProgressError(SimulationElementError):
    pass


class Progress(object):
    """
    Progress: A wrapper for reporting simulation progress
    
    @ivar runs: The number of runs completed
    @type runs: C{int}
    
    """

    progress_qry = xpath.XPathQuery('//progress[@xmlns="%s"]' % collab.COLLAB_NS)
    runs_qry = xpath.XPathQuery('/progress[@xmlns="%s"]/runs' % collab.COLLAB_NS)
    
    def __init__(self, runs=0):
        self.runs = runs

    def toElement(self):
        el = Element((collab.COLLAB_NS, 'progress'))
        el.addElement('runs', content=str(self.runs))
        return el

    @staticmethod
    def fromElement(element):
        if not Progress.progress_qry.matches(element):
            raise InvalidProgressError('No progress')

        runs = 0
        el = Progress.progress_qry.queryForNodes(element)[0]
        try:
            runs = int(Progress.runs_qry.queryForString(el))
        except ValueError as e:
            pass
        
        return Progress(runs)

class InvalidLoggerError(SimulationElementError):
    pass


class Logger(object):
    """
    Logger: wrapper for reporting log messages to some output node

    @ivar logs: A mapping of log types to log messages
    @type logs: C{defaultdict(C{list})}
    
    """

    log_qry = xpath.XPathQuery('//%s[@xmlns="%s"]' % (collab.LOGGER_EL, collab.COLLAB_NS))
    
    def __init__(self):
        self.logs = defaultdict(list)

    def addLog(self, err, msg):
        self.logs[err].append(msg)

    def hasSeverity(self, severity):
        return severity in self.logs

    def toElement(self):
        el = Element((collab.COLLAB_NS, collab.LOGGER_EL))
        for err, msgs in self.logs.items():
            for m in msgs:
                el.addElement(err, content=m)
        return el

    @staticmethod
    def fromElement(element):
        if not Logger.log_qry.matches(element):
            raise InvalidLoggerError('Not a log')

        log = Logger()
        for el in Logger.log_qry.queryForNodes(element)[0].elements():
            if not el.children:
                continue
            log.addLog(el.name, el.children[0])

        return log

        
def getParameters(item, logs):
    try:
        return Parameters.fromElement(item)
    except InvalidParametersError as e:
        logs.addLog(collab.ERROR_EL, str(e))
        
def getDistributions(item, logs):
    try:
        return Distributions.fromElement(item)
    except InvalidDistributionsError as e:
        logs.addLog(collab.ERROR_EL, str(e))

def getProgress(item, logs):
    try:
        return Progress.fromElement(item)
    except InvalidProgressError as e:
        logs.addLog(collab.ERROR_EL, str(e))


        

    
