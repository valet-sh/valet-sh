# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import os
import signal
import json
import ast
import time
import sys
import itertools

from ansible import constants as C
from ansible.plugins.callback.debug import CallbackModule as CallbackModule_debug

class CallbackModule(CallbackModule_debug):
    '''
    Override for the debug callback module.

    Handle .inprogress flag file and error reporting
    '''
    CALLBACK_VERSION = 2.9
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'valet-sh'

    def __init__(self):
        self._output = 1
        self._spinner = itertools.cycle(["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"])
        super(CallbackModule, self).__init__()

    def _debug_enabled(self):
        return os.environ.get('APPLICATION_DEBUG_INFO_ENABLED') == '1'

    def v2_playbook_on_task_start(self, task, is_conditional):
        if self._debug_enabled():
            super(CallbackModule, self)._task_start(task)
        else:
            if self._output == 1:
                print('\x1b[2K', end="\r")
                print("\033[1;32m" + next(self._spinner) + "\033[0m " + task.get_name(), end="\r")

    def v2_runner_on_start(self, host, task):
        if self._debug_enabled():
            super(CallbackModule, self).v2_runner_on_start(host, task)

    def v2_playbook_on_play_start(self, play):
        if self._debug_enabled():
            super(CallbackModule, self).v2_playbook_on_play_start(play)

    def _print_task_banner(self, task):
        if self._debug_enabled():
            super(CallbackModule, self)._print_task_banner(task)

    def v2_runner_on_skipped(self, result):
        if self._debug_enabled():
            super(CallbackModule, self).v2_runner_on_skipped(result)

    def v2_runner_on_ok(self, result):    
        for key in result._result.keys():
            if key == 'vsh_stdout':
                self._output = 0
                print('\x1b[2K', end="\n")
                print(result._result[key])
        if self._debug_enabled():
            super(CallbackModule, self).v2_runner_on_ok(result)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        vsh_msg = ''
        if self._debug_enabled():
            super(CallbackModule, self).v2_runner_on_failed(result, ignore_errors)
        else:
            # get result ansible dict
            resultDict = "%s" % (result._result)
            # convert to json object
            jsonObj = json.loads(json.dumps(ast.literal_eval(resultDict)))
            # get msg from object
            if 'msg' in jsonObj:
                vsh_msg = jsonObj['msg']
            if 'message' in jsonObj:
                vsh_msg = jsonObj['message']
            # display error
            print('\x1b[2K')
            print("\033[1;31m✘ " + vsh_msg + '\033[0m' , end="\n")

    def v2_playbook_on_stats(self, stats):
        if self._debug_enabled():
            super(CallbackModule, self).v2_playbook_on_stats(stats)
        else:
            hosts = sorted(stats.processed.keys())
            for h in hosts:
                t = stats.summarize(h)
                if (t['failures'] == 0) & (self._output == 1):
                    self._output = 0
                    print('\x1b[2K')
                    print("\033[1;32m✔ done\033[0m", end="\n")

    def v2_runner_item_on_ok(self, result):
        if self._debug_enabled():
            super(CallbackModule, self).v2_runner_item_on_ok(result)

    def v2_runner_item_on_skipped(self, result):
        if self._debug_enabled():
            super(CallbackModule, self).v2_runner_item_on_skipped(result)

    def v2_playbook_on_include(self, included_file):
        if self._debug_enabled():
            super(CallbackModule, self).v2_playbook_on_include(included_file)

    def v2_runner_item_on_failed(self, result):
        if self._debug_enabled():
            super(CallbackModule, self).v2_runner_item_on_failed(result)
