# coding=utf-8
# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function, unicode_literals)

__metaclass__ = type

DOCUMENTATION = '''
    callback: valet-sh
    type: notification
    short_description: valet.sh debug log writer
    version_added: historical
    description:
        - Writes all Ansible event output to the valet.sh debug log file.
        - Works alongside ansible.posix.jsonl (the stdout callback) which
          provides structured JSON output for the Go CLI.
    requirements:
      - set as notification callback in ansible.cfg: callbacks_enabled = valet-sh
'''

import os
import time
import logging

from ansible.plugins.callback.default import CallbackModule as CallbackModule_default
from ansible.utils.display import Display
from ansible.module_utils._text import to_bytes, to_text
from logging.handlers import RotatingFileHandler

# Initialise the rotating log file that the Go CLI tails for structured output.
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


class LogDisplay(Display):
    """Routes all Ansible display output to the debug log instead of stdout."""

    def display(self, msg, color=None, stderr=False, screen_only=False, log_only=False, newline=True):
        msg2 = to_bytes(msg.lstrip(u'\n'))
        if __import__('sys').version_info >= (3,):
            msg2 = to_text(msg2)
        logger.log(logging.DEBUG, msg2)


class CallbackModule(CallbackModule_default):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'notification'
    CALLBACK_NAME = 'valet-sh'

    def __init__(self):
        super(CallbackModule, self).__init__()
        # Route all display calls through LogDisplay so every Ansible event
        # is written to debug.log rather than stdout (which belongs to jsonl).
        self._display = LogDisplay()

    def v2_playbook_on_task_start(self, task, is_conditional):
        super(CallbackModule, self)._task_start(task)

    def v2_playbook_on_play_start(self, play):
        super(CallbackModule, self).v2_playbook_on_play_start(play)

    def v2_runner_on_start(self, host, task):
        super(CallbackModule, self).v2_runner_on_start(host, task)

    def v2_runner_on_ok(self, result):
        super(CallbackModule, self).v2_runner_on_ok(result)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        super(CallbackModule, self).v2_runner_on_failed(result, ignore_errors)

    def v2_runner_on_unreachable(self, result):
        super(CallbackModule, self).v2_runner_on_unreachable(result)

    def v2_playbook_on_stats(self, stats):
        super(CallbackModule, self).v2_playbook_on_stats(stats)
