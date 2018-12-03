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

    def _debug_enabled(self):
        return os.environ.get('APPLICATION_DEBUG_INFO_ENABLED')=='1'

    def v2_playbook_on_play_start(self, play):
        # create .inprogress flag file for valet.sh cli spinner to start
        open('/tmp/valet-sh.inprogress', 'a').close()

        # wip: get name of playbook
        #name = play.get_name().strip()
        #if not self._debug_enabled:
        #    self._display.display(name);

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

        delegated_vars = result._result.get('_ansible_delegated_vars', None)
        self._clean_results(result._result, result._task.action)

        if self._play.strategy == 'free' and self._last_task_banner != result._task._uuid:
            self._print_task_banner(result._task)

        self._handle_exception(result._result)
        self._handle_warnings(result._result)

        if result._task.loop and 'results' in result._result:
            self._process_items(result)

        else:
            if delegated_vars:
                if self._debug_enabled():
                    self._display.display("fatal: [%s -> %s]: FAILED! => %s" % (result._host.get_name(), delegated_vars['ansible_host'],
                                                                            self._dump_results(result._result)), color=C.COLOR_ERROR)
            else:
                if self._debug_enabled():
                    self._display.display("fatal: [%s]: FAILED! => %s" % (result._host.get_name(), self._dump_results(result._result)), color=C.COLOR_ERROR)

        if ignore_errors:
            if self._debug_enabled():
                self._display.display("...ignoring", color=C.COLOR_SKIP)
        else:
            if not self._debug_enabled:
                self._display.display(vsh_msg, None, True)
            