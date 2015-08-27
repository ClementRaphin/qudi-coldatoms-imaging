# -*- coding: utf-8 -*-
"""
This file contains the QuDi remote object manager class.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (C) 2015 Jan M. Binder jan.binder@uni-ulm.de
"""


from pyqtgraph.Qt import QtCore
from urllib.parse import urlparse
from rpyc.utils.server import ThreadedServer
from .util.models import DictTableModel, ListTableModel
import rpyc
import socket


class RemoteObjectManager(QtCore.QObject):
    """ This shares modules with other computers and is resonsible
        for obtaining modules shared by other computer.
    """
    def __init__(self, threadManager, logger):
        """ Handle sharing and getting shared modules.
        """
        super().__init__()
        self.hostname = socket.gethostname()
        self.tm = threadManager
        self.logger = logger
        #self.logger.logMsg('Nameserver is: {0}'.format(self.nameserver._pyroUri), msgType='status')
        self.remoteModules = ListTableModel()
        self.remoteModules.headers[0] = 'Remote Modules'
        self.sharedModules = DictTableModel()
        self.sharedModules.headers[0] = 'Shared Modules'

    def makeRemoteService(self):
        """ A function that returns a class containing a module list hat can be manipulated from the host.
        """
        class RemoteModuleService(rpyc.Service):
            """ An RPyC service that has a module list.
            """
            modules = self.sharedModules
            logMsg = self.logger.logMsg
            def on_connect(self):
                """ code that runs when a connection is created
                    (to init the service, if needed)
                """
                self.logMsg('Client connected!')

            def on_disconnect(self):
                """ code that runs when the connection has already closed
                    (to finalize the service, if needed)
                """
                self.logMsg('Client disconnected!')

            def exposed_getModule(self, name):
                """ Return reference to a module in the shared module list.

                  @param str name: unique module name

                  @return object: reference to the module
                """
                if name in self.modules.storage:
                    return self.modules.storage[name]
                else:
                    self.logMsg('Client requested a module that is not shared.', msgType='error')
                    return None

        return RemoteModuleService

    def refresNameserver(self):
        """ Find name server
        """
        #self.nameserver = Pyro4.locateNS()
        pass

    def createServer(self, port):
        """ Start the rpyc modules server on a given port.

          @param int port: port where the server should be running
        """
        thread = self.tm.newThread('rpyc-server')
        self.server = RPyCServer(self.makeRemoteService(), port)
        self.server.moveToThread(thread)
        thread.started.connect(self.server.run)
        thread.start()
        #self.nameserver.register('{0}-{1}'.format(self.hostname, name), server.uri)
        self.logger.logMsg('Started module server at {0} on port {1}'.format(self.hostname, port), msgType='status')

    def stopServer(self):
        """ Stop the remote module server.
        """
        if hasattr(self, 'server'):
            self.server.close()

    def shareModule(self, name, obj):
        """ Add a module to the list of modules that can be accessed remotely.

          @param str name: unique name that is used to access the module
          @param object obj: a reference to the module
        """
        if name in self.sharedModules.storage:
            self.logger.logMsg('Module {0} already shared.'.format(name), msgType='warning')
        self.sharedModules.add(name, obj)
        self.logger.logMsg('Shared module {0}.'.format(name), msgType='status')

    def unshareModule(self, name):
        """ Remove a module from the shared module list.
            
          @param str name: unique name of the module that should not be accessible any more
        """
        if name in self.sharedModules.storage:
            self.logger.logMsg('Module {0} was not shared.'.format(name), msgType='error')
        self.sharedModules.pop(name)

    def getRemoteModuleUrl(self, url):
        """ Get a remote module via its URL.

          @param str url: URL pointing to a module hosted b a remote server
          
          @return object: remote module
        """
        parsed = urlparse(url)
        name = parsed.path.replace('/', '')
        return self.getRemoteModule(parsed.hostname, parsed.port, name)

    def getRemoteModule(self, host, port, name):
        """ Get a remote module via its host, port and name.

          @param str host: host that the remote module server is running on
          @param int port: port that the remote module server is listening on
          @param str name: unique name of the remote module

          @return object: remote module
        """
        module = RemoteModule(host, port, name)
        self.remoteModules.append(module)
        return module.module


class RPyCServer(QtCore.QObject):
    """ Contains a RPyC server that serves modules to remote computers. Runs in a QThread.
    """
    def __init__(self, serviceClass, port):
        """ 
          @param class serviceClass: class that represents an RPyC service
          @param int port: port that hte RPyC server should listen on
        """
        super().__init__()
        self.serviceClass = serviceClass
        self.port = port

    def run(self):
        """ Start the RPyC server
        """
        self.server = ThreadedServer(self.serviceClass, port = self.port, protocol_config = {'allow_all_attrs': True })
        self.server.start()

class RemoteModule:
    """ This class represents a module on a remote computer and holds a reference to it.
    """
    def __init__(self, host, port, name):
        self.connection = rpyc.connect(host, port, config={'allow_all_attrs': True})
        self.module = self.connection.root.getModule(name)
        self.name = name