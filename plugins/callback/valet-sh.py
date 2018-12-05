# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
import json
import ast

from ansible import constants as C
from ansible.plugins.callback.debug import CallbackModule as CallbackModule_debug

class CallbackModule(CallbackModule_debug):

    '''
    Override for the debug callback module.

    Handle .inprogress flag file and error reporting
    '''
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'valet-sh'

    def __init__(self):
        self._play = None
        self._last_task = None
        # create .inprogress flag file for valet.sh cli spinner to start
        open('/tmp/valet-sh.inprogress', 'a').close()
        super(CallbackModule, self).__init__()

    def _debug_enabled(self):
        return os.environ.get('APPLICATION_DEBUG_INFO_ENABLED')=='1'

    def v2_playbook_on_play_start(self, play):
        self._play = play

        # if debug is enabled call super function
        if self._debug_enabled():
            super(CallbackModule, self).v2_playbook_on_play_start(play)

        #else:
        #    if play.name:
        #        self._display.display(play.name, color=C.COLOR_OK)
            

    def _print_task_banner(self, task):
        # if debug is enabled call super function
        if self._debug_enabled():
            super(CallbackModule, self)._print_task_banner(task)
        else:
            if task.name:
                self._last_task = task
            else:
                self._last_task = None


    def v2_runner_on_skipped(self, result):
        # if debug is enabled call super function
        if self._debug_enabled():
            super(CallbackModule, self).v2_runner_on_skipped(result)
        else:
            if (self._last_task):
                self._display.display(u"\u2714  %s" % (self._last_task.name), color=C.COLOR_SKIP)


    def v2_runner_on_ok(self, result):
        for key in result._result.keys():
            if key == 'msg':
                print(result._result[key])

        # if debug is enabled call super function
        if self._debug_enabled():
            super(CallbackModule, self).v2_runner_on_ok(result)
        else:
            if (self._last_task and self._last_task.name):
                self._display.display(u"\u2714  %s" % (self._last_task.name), color=C.COLOR_OK)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        vsh_msg = ''
        # if debug is enabled call super function
        if self._debug_enabled():
            super(CallbackModule, self).v2_runner_on_failed(result, ignore_errors)
        else:
            # get result ansible dict
            resultDict = "%s" % (result._result)
            # convert to json object
            jsonObj = json.loads(json.dumps(ast.literal_eval(resultDict)))
            # get msg from object
            if 'msg' in jsonObj :
                vsh_msg = jsonObj['msg']
            if 'message' in jsonObj :
                vsh_msg = jsonObj['message']
            # display error
            self._display.error(vsh_msg)


    def v2_playbook_on_stats(self, task):
        # remove .inprogress flag file for valet.sh cli spinner to stop
        os.unlink('/tmp/valet-sh.inprogress')
        # if debug is enabled call super function
        if self._debug_enabled():
            super(CallbackModule, self).v2_playbook_on_stats(task)

    def v2_runner_item_on_ok(self, result):
        # if debug is enabled call super function
        if self._debug_enabled():
            super(CallbackModule, self).v2_runner_item_on_ok(result)


    def v2_runner_item_on_skipped(self, result):
        # if debug is enabled call super function
        if self._debug_enabled():
            super(CallbackModule, self).v2_runner_item_on_skipped(result)


    def v2_playbook_on_include(self, included_file):
        # if debug is enabled call super function
        if self._debug_enabled():
            super(CallbackModule, self).v2_playbook_on_include(included_file)


    def v2_runner_item_on_failed(self, result):
        # if debug is enabled call super function
        if self._debug_enabled():
            super(CallbackModule, self).v2_runner_item_on_failed(result)

            