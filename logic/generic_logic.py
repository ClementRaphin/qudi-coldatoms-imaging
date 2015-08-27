# -*- coding: utf-8 -*-
"""
This file contains the QuDi logic module base class.

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

from core.base import Base
from core.util.mutex import Mutex
from pyqtgraph.Qt import QtCore
from fysom import Fysom
from core.util.models import DictTableModel

class GenericLogic(Base):
    """A generic logic interface class.
    """
    _modclass = 'GenericLogic'
    _modtype = 'Logic'
    _tasks = DictTableModel()
    
    def __init__(self, manager, name, configuation, callbacks, **kwargs):
        """ Initialzize a logic module.

          @param object manager: Manager object that has instantiated this object
          @param str name: unique module name
          @param dict configuration: module configuration as a dict
          @param dict callbacks: dict of callback functions for Fysom state machine
          @param dict kwargs: dict of additional arguments
        """
        super().__init__(manager, name, configuation, callbacks, **kwargs)
        self.taskLock = Mutex()
        
    def getModuleThread(self):
        """ Get the thread associated to this module.

          @return QThread: thread with qt event loop associated with this module
        """
        return self._manager.tm._threads['mod-logic-' + self._name].thread

    def registerTask(self, task):
        with self.taskLock:
            if self._tasks.add(task.name, task) == None:
                self.logMsg('Could not register task {} because a task is already registered with this name.'.format(task.name), msgType='error')
                return -1
            return 0

class TaskResult(QtCore.QObject):
    def __init__(self):
        super().__init__()
        self.data = None
        self.success = None

    def updata(self, data, success=None):
        self.data = data
        self.success = success

class InterruptableTask(QtCore.QObject, Fysom):
    """ This class represents a task in a module that can be safely executed by checking preconditions
        and pausing other tasks that are being executed as well.
    """
    sigPaused = QtCore.Signal()
    sigResumed = QtCore.Signal()
    sigExecutionStarted = QtCore.Signal()
    sigExecutionFinished = QtCore.Signal()

    def __init__(self, name, function, args=[], kwargs={}):
        QtCore.QObject.__init__(self)
        _default_callbacks = {'run': self._run, 'pause': self._pause, 'resume': self._resume, 'finish': self._finish}
        _stateList = {
            'initial': 'stopped',
            'events': [
                {'name': 'run', 'src': 'stopped', 'dst': 'running'},
                {'name': 'pause', 'src': 'running', 'dst': 'paused'},
                {'name': 'finish', 'src': 'running', 'dst': 'stopped'},
                {'name': 'resume', 'src': 'paused', 'dst': 'running'}
            ],
            'callbacks': _default_callbacks
        }
        Fysom.__init__(self)
        self.lock = Mutex()
        self.name = name
        self.func = function
        self.args = args
        self.interruptable = False
        self.success = False

    def makeInterruptable(self, pausefunction, resumefunction):
        if callable(self.pausefunction) and callable(resumefunction):
            self.pausefunction = pausefunction
            self.resumefuncion = resumefunction
            self.interruptable = True

    def _run(self, e):
        self.result = TaskResult()
        try:
            if callable(self.function):
                 self.function(*self.args, **self.kwargs)
            else:
               self.result.update(None, False)
        except Exception as e:
            self.logMsg('Exception during task {}. {}'.format(self.name, e), msgType='error')
            self.result.update(None, False)
            
                
    def _pause(self, e):
        try:
            if callable(self.function):
                 self.function(*self.args, **self.kwargs)
            else:
               self.result.update(None, False)
        except Exception as e:
            self.logMsg('Exception during task {}. {}'.format(self.name, e), msgType='error')
            self.result.update(None, False)
 
        self.sigPaused.emit()

    def _resume(self, e):
        try:
            if callable(self.function):
                 self.function(*self.args, **self.kwargs)
            else:
               self.result.update(None, False)
        except Exception as e:
            self.logMsg('Exception during task {}. {}'.format(self.name, e), msgType='error')
            self.result.update(None, False)
 
        self.sigResumed.eimit()

    def _finish(self, e):
        result.update(self.result, self.success)
        self.sigFinished.emit()

    def canPause(self):
        return self.interruptable and self.can('pause')

class PrePostTask(QtCore.QObject, Fysom):

    sigPreExecStart = QtCore.Signal()
    sigPreExecFinish = QtCore.Signal()
    sigPostExecStart = QtCore.Signal()
    sigPostExecFinish = QtCore.Signal()

    def __init__(self, name, function, args=[]):
        QtCore.QObject.__init__()
        _default_callbacks = {'prerun': self.preExecute, 'postrun': self.postExecute}
        _stateList = {
            'initial': 'stopped',
            'events': [
                {'name': 'prerun', 'src': 'stopped', 'dst': 'paused'},
                {'name': 'postrun', 'src': 'paused', 'dst': 'stopped'}
            ],
            'callbacks': _default_callbacks
        }
        Fysom.__init__()
        self.lock = Mutex()
        self.name = name
        self.func = function
        self.args = args

    def preExecute(self):
        self.sigPreExecStart.emit()

        self.sigPreExecFinish.emit()

    def postExecute(self):
        self.sigPostExecStart.emit()

        self.sigPostExecFinish.emit()

    def canPause():
        return False
