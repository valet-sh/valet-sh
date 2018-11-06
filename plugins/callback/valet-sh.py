# (c) 2018 TechDivision GmbH
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import os
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
        # create .inprogress flag file for valet.sh cli spinner to start
        open('.inprogress', 'a').close()
        # call parent class function
        super(CallbackModule, self).__init__()

    def v2_playbook_on_stats(self, task):
        # remove .inprogress flag file for valet.sh cli spinner to stop
        os.unlink('.inprogress')
        # call parent class function
        super(CallbackModule, self).v2_playbook_on_stats(task)

    def v2_runner_on_failed(self, result, ignore_errors=False):

        # todo: parse result, reformat it and output to parent stdout
        # self._display.display("%s" % (result._result))

        # call parent class function
        super(CallbackModule, self).v2_runner_on_failed(result, ignore_errors)
