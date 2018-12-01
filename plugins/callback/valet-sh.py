# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
import json
import ast
from ansible.plugins.callback.debug import CallbackModule as CallbackModule_debug

class CallbackModule(CallbackModule_debug):

    '''
    Override for the debug callback module.

    Handle .inprogress flag file and error reporting
    '''
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'valet-sh'

    def _debug_enabled(self):
        return os.environ.get('APPLICATION_DEBUG_INFO_ENABLED')=='1'

    def v2_playbook_on_play_start(self, play):
        # create .inprogress flag file for valet.sh cli spinner to start
        open('/tmp/valet-sh.inprogress', 'a').close()

        # wip: get name of playbook
        #name = play.get_name().strip()

        self._play = play

        # if debug is enabled call super function
        if self._debug_enabled():
            super(CallbackModule, self).v2_playbook_on_play_start(play)
            

    def _print_task_banner(self, task):
        # if debug is enabled call super function
        if self._debug_enabled():
            super(CallbackModule, self)._print_task_banner(task)


    def v2_runner_on_skipped(self, result):
        # if debug is enabled call super function
        if self._debug_enabled():
            super(CallbackModule, self).v2_runner_on_skipped(result)


    def v2_runner_on_ok(self, result):
        # if debug is enabled call super function
        if self._debug_enabled():
            super(CallbackModule, self).v2_runner_on_ok(result)


    def v2_playbook_on_stats(self, task):
        # remove .inprogress flag file for valet.sh cli spinner to stop
        os.unlink('/tmp/valet-sh.inprogress')
        # if debug is enabled call super function
        if self._debug_enabled():
            super(CallbackModule, self).v2_playbook_on_stats(task)


    def v2_runner_on_failed(self, result, ignore_errors=False):
        # get result ansible dict
        resultDict = "%s" % (result._result)

        # convert to json object
        jsonObj = json.loads(json.dumps(ast.literal_eval(resultDict)))
        # get msg from object
        if 'msg' in jsonObj :
            vsh_msg = jsonObj['msg']
        if 'message' in jsonObj :
            vsh_msg = jsonObj['message']

        # send msg to stderr
        self._display.display(vsh_msg, None, True)

        # call parent class function
        super(CallbackModule, self).v2_runner_on_failed(result, ignore_errors)
