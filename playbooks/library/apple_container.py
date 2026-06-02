#!/usr/bin/python
# -*- coding: utf-8 -*-

from ansible.module_utils.basic import AnsibleModule
import subprocess
import json
import shlex


def run_cli(args, check=False):
    """Run the container CLI and return (rc, stdout, stderr)."""
    cmd = ['container'] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def container_inspect(name):
    """Return parsed inspect dict for a container, or None if not found."""
    rc, stdout, stderr = run_cli(['inspect', name])
    if rc != 0:
        return None
    try:
        data = json.loads(stdout)
        if isinstance(data, list):
            return data[0] if data else None
        return data
    except (ValueError, KeyError):
        return None


def container_state(info):
    """Return normalised state string from inspect output."""
    if info is None:
        return 'absent'
    status = ''
    if 'State' in info:
        status = info['State'].get('Status', '').lower()
    elif 'status' in info:
        status = info['status'].lower()
    if status in ('running',):
        return 'running'
    return 'stopped'


def build_run_args(params):
    args = ['run']
    if params['detach']:
        args.append('-d')
    if params['remove']:
        args.append('--rm')
    if params['name']:
        args += ['--name', params['name']]
    for port in (params['ports'] or []):
        args += ['-p', port]
    for vol in (params['volumes'] or []):
        args += ['-v', vol]
    for env in (params['env'] or []):
        args += ['-e', env]
    args.append(params['image'])
    cmd = params['command'] or []
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    args += cmd
    return args


def ensure_started(module, params, info, current_state):
    changed = False
    msg = ''

    if current_state == 'absent':
        if not module.check_mode:
            rc, stdout, stderr = run_cli(build_run_args(params))
            if rc != 0:
                module.fail_json(msg='Failed to run container', stderr=stderr, rc=rc)
        changed = True
        msg = 'Container created and started'

    elif current_state == 'stopped':
        if not module.check_mode:
            rc, stdout, stderr = run_cli(['start', params['name']])
            if rc != 0:
                module.fail_json(msg='Failed to start container', stderr=stderr, rc=rc)
        changed = True
        msg = 'Container started'

    else:
        msg = 'Container already running'

    return changed, msg


def ensure_stopped(module, params, info, current_state):
    changed = False
    msg = ''

    if current_state == 'running':
        if not module.check_mode:
            rc, stdout, stderr = run_cli(['stop', params['name']])
            if rc != 0:
                module.fail_json(msg='Failed to stop container', stderr=stderr, rc=rc)
        changed = True
        msg = 'Container stopped'

    elif current_state == 'absent':
        msg = 'Container does not exist'

    else:
        msg = 'Container already stopped'

    return changed, msg


def ensure_present(module, params, info, current_state):
    """Container must exist (created) but need not be running."""
    if current_state != 'absent':
        return False, 'Container already present'

    args = build_run_args(params)
    # Create without necessarily keeping it running — add --rm=false explicitly
    # For "present" we create but immediately stop if image starts automatically.
    # Simplest: run detached, then stop right away if detach wasn't requested.
    args_detached = ['run', '-d', '--name', params['name']]
    for port in (params['ports'] or []):
        args_detached += ['-p', port]
    for vol in (params['volumes'] or []):
        args_detached += ['-v', vol]
    for env in (params['env'] or []):
        args_detached += ['-e', env]
    args_detached.append(params['image'])

    if not module.check_mode:
        rc, stdout, stderr = run_cli(args_detached)
        if rc != 0:
            module.fail_json(msg='Failed to create container', stderr=stderr, rc=rc)
        # Stop immediately so it is "present but not running"
        rc2, _, stderr2 = run_cli(['stop', params['name']])
        if rc2 != 0:
            module.fail_json(msg='Container created but could not be stopped', stderr=stderr2, rc=rc2)

    return True, 'Container created'


def ensure_absent(module, params, info, current_state):
    if current_state == 'absent':
        return False, 'Container already absent'

    if not module.check_mode:
        if current_state == 'running':
            run_cli(['stop', params['name']])
        rc, stdout, stderr = run_cli(['delete', params['name']])
        if rc != 0:
            module.fail_json(msg='Failed to remove container', stderr=stderr, rc=rc)

    return True, 'Container removed'


def main():
    module_args = dict(
        name=dict(type='str', required=True),
        image=dict(type='str', required=False),
        state=dict(type='str', default='started',
                   choices=['started', 'stopped', 'present', 'absent']),
        ports=dict(type='list', elements='str', required=False, default=[]),
        volumes=dict(type='list', elements='str', required=False, default=[]),
        env=dict(type='list', elements='str', required=False, default=[]),
        detach=dict(type='bool', default=True),
        remove=dict(type='bool', default=False),
        command=dict(type='raw', required=False, default=[]),
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    params = module.params

    state = params['state']

    if state in ('started', 'present') and not params['image']:
        module.fail_json(msg="Parameter 'image' is required when state is '%s'" % state)

    info = container_inspect(params['name'])
    current_state = container_state(info)

    dispatch = {
        'started': ensure_started,
        'stopped': ensure_stopped,
        'present': ensure_present,
        'absent': ensure_absent,
    }

    changed, msg = dispatch[state](module, params, info, current_state)

    module.exit_json(changed=changed, msg=msg, name=params['name'], state=state)


if __name__ == '__main__':
    main()