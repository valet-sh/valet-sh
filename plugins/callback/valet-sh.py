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

    def v2_playbook_on_play_start(self, play):
        # create .inprogress flag file for valet.sh cli spinner to start
        open('/tmp/valet-sh.inprogress', 'a').close()
        name = play.get_name().strip()
        self._play = play
        #self._display.banner(msg)

    def _print_task_banner(self, task):
        return True

    def v2_runner_on_skipped(self, result):
        return True

    def v2_runner_on_ok(self, result):
        return True        

    def v2_playbook_on_stats(self, task):
        # remove .inprogress flag file for valet.sh cli spinner to stop
        os.unlink('/tmp/valet-sh.inprogress')
        # call parent class function
        #super(CallbackModule, self).v2_playbook_on_stats(task)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        # get result ansible dict
        resultDict = "%s" % (result._result)

        # convert to json object
        jsonObj = json.loads(json.dumps(ast.literal_eval(resultDict)))
        # get msg from object
        if 'msg' in jsonObj :
            msg = jsonObj['msg']
        if 'message' in jsonObj :
            msg = jsonObj['message']

        # send msg to stderr
        self._display.display(msg, None, True)

        # call parent class function
        super(CallbackModule, self).v2_runner_on_failed(result, ignore_errors)
