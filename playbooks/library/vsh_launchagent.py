#!/usr/bin/python
# -*- coding: utf-8 -*-

from ansible.module_utils.basic import AnsibleModule
import subprocess
import os
import re
import time


def run_launchctl(args):
    cmd = ['launchctl'] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def plist_path(label, scope):
    if scope == 'gui':
        return os.path.expanduser(f'~/Library/LaunchAgents/{label}.plist')
    return f'/Library/LaunchDaemons/{label}.plist'


def domain_target(scope, uid):
    return f'gui/{uid}' if scope == 'gui' else 'system'


def service_target(scope, uid, label):
    return f'gui/{uid}/{label}' if scope == 'gui' else f'system/{label}'


def current_state(label):
    rc, stdout, _ = run_launchctl(['list', label])
    if rc != 0:
        return 'absent'
    if re.search(r'"PID"\s*=\s*\d+', stdout):
        return 'running'
    return 'stopped'


def ensure_present(module, label, scope, uid, path, state):
    if state != 'absent':
        return False, 'LaunchAgent already registered'
    if not os.path.exists(path):
        module.fail_json(msg=f'Plist not found: {path}')
    if not module.check_mode:
        rc, _, stderr = run_launchctl(['bootstrap', domain_target(scope, uid), path])
        if rc != 0:
            module.fail_json(msg='Failed to bootstrap LaunchAgent', stderr=stderr)
    return True, 'LaunchAgent registered'


def ensure_absent(module, label, scope, uid, state):
    if state == 'absent':
        return False, 'LaunchAgent already absent'
    if not module.check_mode:
        rc, _, stderr = run_launchctl(['bootout', service_target(scope, uid, label)])
        if rc != 0:
            module.fail_json(msg='Failed to bootout LaunchAgent', stderr=stderr)
    return True, 'LaunchAgent unregistered'


def ensure_started(module, label, scope, uid, path, state):
    if state == 'running':
        return False, 'LaunchAgent already running'
    if not module.check_mode:
        if state == 'absent':
            if not os.path.exists(path):
                module.fail_json(msg=f'Plist not found: {path}')
            rc, _, stderr = run_launchctl(['bootstrap', domain_target(scope, uid), path])
            if rc != 0:
                module.fail_json(msg='Failed to bootstrap LaunchAgent', stderr=stderr)
        rc, _, stderr = run_launchctl(['kickstart', service_target(scope, uid, label)])
        if rc != 0:
            module.fail_json(msg='Failed to start LaunchAgent', stderr=stderr)
    return True, 'LaunchAgent started'


def ensure_stopped(module, label, scope, uid, state):
    if state == 'absent':
        return False, 'LaunchAgent not registered'
    if state == 'stopped':
        return False, 'LaunchAgent already stopped'
    if not module.check_mode:
        rc, _, stderr = run_launchctl(['kill', 'SIGTERM', service_target(scope, uid, label)])
        if rc != 0:
            module.fail_json(msg='Failed to stop LaunchAgent', stderr=stderr)
    return True, 'LaunchAgent stopped'


def ensure_restarted(module, label, scope, uid, path, state):
    if not module.check_mode:
        if state == 'absent':
            if not os.path.exists(path):
                module.fail_json(msg=f'Plist not found: {path}')
            rc, _, stderr = run_launchctl(['bootstrap', domain_target(scope, uid), path])
            if rc != 0:
                module.fail_json(msg='Failed to bootstrap LaunchAgent', stderr=stderr)
        rc, _, stderr = run_launchctl(['kickstart', '-k', service_target(scope, uid, label)])
        if rc != 0:
            module.fail_json(msg='Failed to restart LaunchAgent', stderr=stderr)
    return True, 'LaunchAgent restarted'


def ensure_reloaded(module, label, scope, uid, path, state):
    if not os.path.exists(path):
        module.fail_json(msg=f'Plist not found: {path}')
    if not module.check_mode:
        run_launchctl(['bootout', service_target(scope, uid, label)])
        rc, _, stderr = bootstrap_with_retry(scope, uid, path)
        if rc != 0:
            module.fail_json(msg='Failed to reload LaunchAgent', stderr=stderr)
    return True, 'LaunchAgent reloaded'


def bootstrap_with_retry(scope, uid, path, retries=5, delay=1.0):
    for attempt in range(retries):
        rc, stdout, stderr = run_launchctl(['bootstrap', domain_target(scope, uid), path])
        if rc == 0:
            return rc, stdout, stderr
        if attempt < retries - 1:
            time.sleep(delay)
    return rc, stdout, stderr


def do_daemon_reload(module, label, scope, uid, path, svc_state):
    if not os.path.exists(path):
        module.fail_json(msg=f'Plist not found: {path}')
    if not module.check_mode:
        bootout_rc, _, bootout_stderr = run_launchctl(['bootout', service_target(scope, uid, label)])
        rc, _, stderr = bootstrap_with_retry(scope, uid, path)
        if rc != 0:
            module.fail_json(
                msg='Failed to reload LaunchAgent',
                stderr=stderr,
                bootout_rc=bootout_rc,
                bootout_stderr=bootout_stderr,
            )


def main():
    module_args = dict(
        label=dict(type='str', required=True),
        state=dict(type='str', default='started',
                   choices=['started', 'stopped', 'restarted', 'reloaded', 'present', 'absent']),
        scope=dict(type='str', default='gui', choices=['gui', 'system']),
        daemon_reload=dict(type='bool', default=False),
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    params = module.params

    label = params['label']
    state = params['state']
    scope = params['scope']
    uid = os.getuid()
    path = plist_path(label, scope)
    svc_state = current_state(label)

    reload_changed = False
    if params['daemon_reload'] and state != 'absent':
        do_daemon_reload(module, label, scope, uid, path, svc_state)
        reload_changed = True
        svc_state = current_state(label)

    dispatch = {
        'present':   lambda: ensure_present(module, label, scope, uid, path, svc_state),
        'absent':    lambda: ensure_absent(module, label, scope, uid, svc_state),
        'started':   lambda: ensure_started(module, label, scope, uid, path, svc_state),
        'stopped':   lambda: ensure_stopped(module, label, scope, uid, svc_state),
        'restarted': lambda: ensure_restarted(module, label, scope, uid, path, svc_state),
        'reloaded':  lambda: ensure_reloaded(module, label, scope, uid, path, svc_state),
    }

    state_changed, msg = dispatch[state]()
    module.exit_json(changed=reload_changed or state_changed, msg=msg, label=label, state=state, plist=path)


if __name__ == '__main__':
    main()