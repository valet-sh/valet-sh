# coding=utf-8
# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function, unicode_literals)

__metaclass__ = type

DOCUMENTATION = '''
    callback: valet-sh
    type: stdout
    short_description: valet.sh Ansible screen output
    version_added: historical
    description:
        - This is the valet-sh output callback for ansible-playbook.
    extends_documentation_fragment:
      - default_callback
    requirements:
      - set as stdout in configuration
'''

import os
import signal
import json
import ast
import time
import sys
import logging
import itertools

from ansible import constants as C

from ansible.plugins.callback.default import CallbackModule as CallbackModule_default
from ansible.utils.display import Display
from ansible.module_utils._text import to_bytes, to_text
from logging.handlers import RotatingFileHandler

# init logger
logger = logging.getLogger('valet-sh')
logger.setLevel(logging.DEBUG)
if not os.path.exists('log'):
    os.makedirs('log')
vsh_log_filename = 'log/debug.log'
fh = RotatingFileHandler(vsh_log_filename, backupCount=9)
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)
logger.handlers[0].doRollover()
logger.debug('---------------------------------------------')
logger.debug('Log started on %s.' % time.asctime())
logger.debug('---------------------------------------------\n')

# output colors and cursor codes
RED     = "\033[1;31m"
BLUE    = "\033[1;34m"
CYAN    = "\033[1;36m"
GREEN   = "\033[0;32m"
RESET   = "\033[0;0m"
BOLD    = "\033[;1m"
REVERSE = "\033[;7m"
FLUSH   = "\x1b[2K"
CURSOR_HIDE = "\033[?25l"
CURSOR_SHOW = "\033[?25h"

print(CURSOR_SHOW, end="")

class LogDisplay(Display):
    def display(self, msg, color=None, stderr=False, screen_only=False, log_only=False, newline=True):
        msg2 = to_bytes(msg.lstrip(u'\n'))
        if sys.version_info >= (3,):
            msg2 = to_text(msg2, self._output_encoding(stderr=stderr))
        lvl = logging.DEBUG
        logger.log(lvl, msg2)

class CallbackModule(CallbackModule_default):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'valet-sh'

    def _debug_enabled(self):
        return os.environ.get('APPLICATION_DEBUG_INFO_ENABLED') == '1'

    def __init__(self):
        super(CallbackModule, self).__init__()
        self._output = 1
        self._spinner = itertools.cycle(["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"])
        if not self._debug_enabled():
            self._display = LogDisplay()

    def v2_playbook_on_task_start(self, task, is_conditional):
        if not self._debug_enabled():
            if self._output == 1:
                taskname_orig = task.get_name()
                taskname = (taskname_orig[:75] + '...') if len(taskname_orig) > 75 else taskname_orig
                print(FLUSH, end="\r")
                print(GREEN + next(self._spinner) + RESET + " " + taskname, end="\r")
        super(CallbackModule, self)._task_start(task)

    def v2_playbook_on_play_start(self, play):
        super(CallbackModule, self).v2_playbook_on_play_start(play)
        if not self._debug_enabled():
            name = play.get_name().strip()
            print(BLUE + "▶ " + BOLD + name + RESET + CURSOR_HIDE, end="\n")

    def v2_runner_on_start(self, host, task):
        self._plugin_options = C.config.get_plugin_options("callback", "default")
        super(CallbackModule, self).v2_runner_on_start(host, task)

    def v2_runner_on_ok(self, result):
        if not self._debug_enabled():
            for key in result._result.keys():
                if key == 'vsh_stdout':
                    self._output = 0
                    print(FLUSH, end="\n")
                    print(result._result[key] + CURSOR_SHOW)
        super(CallbackModule, self).v2_runner_on_ok(result)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        if not self._debug_enabled():
            vsh_msg = ''

            if 'msg' in result._result:
                vsh_msg = '%s' % (result._result['msg'])

            if 'results' in result._result:
                if result._result['results'][0]:
                    if 'msg' in result._result['results'][0]:
                        vsh_msg = '%s' % (result._result['results'][0]['msg'])
                    if 'stderr' in result._result['results'][0]:
                        vsh_msg += '\n%s' % (result._result['results'][0]['stderr'])
                    if 'module_stderr' in result._result['results'][0]:
                        vsh_msg += '\n%s' % (result._result['results'][0]['module_stderr'])

            if not ignore_errors:
                print(FLUSH)
                print(RED + "✘ " + vsh_msg + RESET, end="\n")
                print(BLUE + "ℹ " + "check /usr/local/valet-sh/valet-sh/log/debug.log" + RESET + CURSOR_SHOW, end="\n")
        super(CallbackModule, self).v2_runner_on_failed(result, ignore_errors)

    def v2_playbook_on_stats(self, stats):
        if not self._debug_enabled():
            hosts = sorted(stats.processed.keys())
            for h in hosts:
                t = stats.summarize(h)
                if (t['failures'] == 0) & (self._output == 1):
                    self._output = 0
                    print(FLUSH)
                    print(GREEN + "✔ done" + RESET + CURSOR_SHOW, end="\n")
        super(CallbackModule, self).v2_playbook_on_stats(stats)