About:
----------------------------------------------------------------------------------------------------

Collab, the power of cloud computing effortlessly built out of your current hardware.

The Collab system allows businesses to build efficient, safe and fault tolerant modeling systems by combining the power of their existing computing infrastructure.

Collab is based on the Extensible Messaging and Presence Protocol (XMPP), more information on XMPP can be found at <http://xmpp.org/>.

Requirements:
----------------------------------------------------------------------------------------------------

 - Python 2.6 or higher
 - Twisted 10.1.0 or higher
 - Wokkel 0.6.3 or higher
 - Scipy 0.9.0 or higher
 - Pysparse 1.2 or higher (if using the 'sparse' copula)
 - Mock 0.7.2 or higher (for tests only)

 - An XMPP server (for running the system) - I use Ejabberd <www.ejabberd.im>

Obtaining:
----------------------------------------------------------------------------------------------------

After installing all requirements listed above and making sure that all packages are available from within your python environment, create a directory for collab e.g.

$ mkdir <ROOT>

where <ROOT> is the path to where you want to keep collab.

Then either 
;; not done yet
;; a) download the latest tarball from <pypi> to <ROOT> and unpack (here XXX refers to whatever collab version you have chosen), 

;; $ tar -xvf <ROOT>/collabXXX.tar.gz  

or
b) clone the source code directly,

$ cd <ROOT>
$ git clone git://github.com/wyn/collab.git

Installation (optional):
----------------------------------------------------------------------------------------------------

To install use the standard setup.py script provided,

$ cd <COLLAB>
$ python setup.py install

where <COLLAB> is the path to your collab source code, <ROOT>/src/python/collab (this directory should be the one with the setup.py script).

Notes:
The install step may need root permissions, use --prefix option if preferred.
See python setup.py --help for other options.

You should now be able to import collab from within your Python environment without errors:

$ python
>>> import collab
>>>

if not then check that collab is reachable from your Python environment,

>>> import sys
>>> print sys.path

or check that collab source code is reachable from your $PYTHONPATH environment variable.

Testing:
----------------------------------------------------------------------------------------------------

Collab comes with a set of unit tests found in <COLLAB>/collab/test/
To run them use the Twisted test runner Trial,

$ cd <COLLAB>
$ trial collab/test/*Tests.py

See trial --help for more details about trial or read the Twisted documentation <http://twistedmatrix.com/trac/wiki/TwistedTrial>.

Notes
 - the tests are self contained and therefore do not require a connection to a running XMPP server.
 - the -u flag can be useful for tracking down intermittent bugs, it tells trial to loop through the tests until an error occurs.

Running a Collab service
----------------------------------------------------------------------------------------------------

For this section you will need a running XMPP server configured correctly.

Collab services are run as external XMPP components implemented as Twisted plugins.  From within the <COLLAB> directory you should be able to view the plugins using the twistd plugin harness,

$ cd <COLLAB>
$ twistd --help

should produce help information including a Commands section containing the five Collab services available:

Commands:
    ...
    collab_proxy_var                  A proxy service for the Collab system VaR calculation
    collab_system_manager             A system manager service for the Collab system
    collab_portfolios_manager         A portfolio manager service for the Collab system
    collab_simulations_manager        A simulation manager service for the Collab system
    collab_distributions_manager      A distributions manager service for the Collab system
    ...


Further help for a particular command NAME can be found with

$ twistd NAME --help

To run a Collab service the XMPP server has to be told that that particular service has permission to send and receive messages.  For Ejabberd the configuration file ejabberd.cfg has to be modified in the 'Listening Ports' section to include the service that you want to allow, for example the entry:

%%%.   ===============
%%%'   LISTENING PORTS

%%
%% listen: The ports ejabberd will listen on, which service each is handled
%% by and what options to start it with.
%%
{listen,
 [

...,

  {10001, ejabberd_service, [
  			    {access, all}, 
  			    {shaper_rule, fast},
  			    {hosts, ["collabproxyvar.collab.coshx"],
  			     [{password, "password"}]
  			    }
  			   ]},

...,

 ]

}.

would allow a service called 'collabproxyvar' to run on the 'collab.coshx' virtual host using port 10001.  Note that this reconfiguration could also be done through the Ejabberd web admin interface, see <www.ejabberd.im> for more details.

Once the XMPP server is configured and restarted the twisted service itself can then be run with the twistd command:

$ cd <COLLAB>
$ twistd -n --pidfile='collab_proxy_var.pid' collab_proxy_var --jid='collabproxyvar.collab.coshx' --rport=10001 --rhost=collab.coshx --secret='password'

A successful start should simply log some startup and handshake messages, an unsuccessful start would shut itself down.  More detailed logging can be shown by passing the --verbose flag,

$ twistd -n --pidfile='collab_proxy_var.pid' collab_proxy_var --jid='collabproxyvar.collab.coshx' --rport=10001 --rhost=collab.coshx --secret='password' --verbose

The salient points here are:
 - Get the name of the service correct, e.g. collab_proxy_var.  This is the command NAME for twistd not ejabberd.
 - The jid of the service matches the name in the 'hosts' entry of the ejabberd_service entry e.g. collabproxyvar.collab.coshx.
 - The rport and rhost match up to the configured settings and that there is a virtual host on the XMPP server called 'collab.coshx'.
 - The --secret matches the configured 'password' setting for that listener.

Notes, 
 - the -n flag tells twistd to run as a shell process rather than a daemon.
 - the --pidfile option simply creates a pid file to allow you to kill a twistd process easily, simply do

$ kill `cat collab_proxy_var.pid`

Resources
----------------------------------------------------------------------------------------------------

The Collab homepage is <https://github.com/wyn/collab>

The wiki pages contain more detailed descriptions of the various steps described here, particularly the configuration of the XMPP server and running the Collab components.

Here are some web resources I found useful:

Twisted:

 - Dave Peticolas has written a very useful and readable introduction to Twisted/asynchronous programming <http://krondo.com/?p=1209>

 - There is also the Twisted documentation <http://twistedmatrix.com/documents/current/core/howto/index.html>

Twisted/XMPP: 

 - Jack Moffit's website has some useful examples of Twisted/Wokkel and XMPP <http://metajack.im/2008/09/25/an-xmpp-echo-bot-with-twisted-and-wokkel/>

 - Ralph Meijer's website also has some examples <http://wokkel.ik.nu/wiki/XMPPClients>

General:

 - I have found the Nullege search engine to be very useful <http://nullege.com/>, simply search for examples of usage of whatever is confusing.

Copyright and Disclaimer
----------------------------------------------------------------------------------------------------

The code in this distribution is Copyright (c) 2010-2011 Simon Parry, unless
excplicitely specified otherwise.

Collab is made available under the LGPL License. The included LICENSE file
describes this in detail.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Contributors
----------------------------------------------------------------------------------------------------
 - Contributors needed

Author
----------------------------------------------------------------------------------------------------

Simon Parry
<simon.parry@coshx.co.uk>
