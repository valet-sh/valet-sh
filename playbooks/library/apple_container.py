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
        state_val = info['State']
        if isinstance(state_val, dict):
            status = state_val.get('Status', '').lower()
        elif isinstance(state_val, str):
            status = state_val.lower()
    elif 'status' in info:
        status_val = info['status']
        if isinstance(status_val, str):
            status = status_val.lower()
        elif isinstance(status_val, dict):
            inner = status_val.get('status', status_val.get('State', status_val.get('state', '')))
            status = inner.lower() if isinstance(inner, str) else ''
    if status == 'running':
        return 'running'
    return 'stopped'


def container_image_ref(info):
    """Extract the image reference from container inspect data.
    Apple container inspect stores it at configuration.image.reference."""
    try:
        return info['configuration']['image']['reference']
    except (KeyError, TypeError):
        return None


def normalize_image_ref(ref):
    """Add docker.io/ prefix when no registry is specified."""
    if not ref:
        return ref
    first = ref.split('/')[0]
    if '.' not in first and ':' not in first and first != 'localhost':
        return 'docker.io/' + ref
    return ref


def image_matches(info, desired):
    """Return True if the container already uses the desired image."""
    current = container_image_ref(info)
    if current is None:
        return False
    return normalize_image_ref(current) == normalize_image_ref(desired)


def _stop_and_delete(module, name, current_state):
    if current_state == 'running':
        rc, _, stderr = run_cli(['stop', name])
        if rc != 0:
            module.fail_json(msg='Failed to stop container', stderr=stderr, rc=rc)
    rc, _, stderr = run_cli(['delete', name])
    if rc != 0:
        module.fail_json(msg='Failed to delete container', stderr=stderr, rc=rc)


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
    if params['cpus']:
        args += ['--cpus', str(params['cpus'])]
    if params['memory']:
        args += ['--memory', params['memory']]
    if params['user']:
        args += ['--user', params['user']]
    args.append(params['image'])
    cmd = params['command'] or []
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    args += cmd
    return args


def ensure_started(module, params, info, current_state):
    # Container exists but uses a different image → recreate
    if current_state != 'absent' and params['image'] and not image_matches(info, params['image']):
        if not module.check_mode:
            _stop_and_delete(module, params['name'], current_state)
            rc, _, stderr = run_cli(build_run_args(params))
            if rc != 0:
                module.fail_json(msg='Failed to run container', stderr=stderr, rc=rc)
        return True, 'Container recreated with updated image'

    # --rm containers auto-delete on stop so they can only be absent or running
    if current_state == 'absent' or (current_state == 'stopped' and params['remove']):
        if not params['image']:
            module.fail_json(msg="Parameter 'image' is required to create container '%s'" % params['name'])
        if not module.check_mode:
            rc, _, stderr = run_cli(build_run_args(params))
            if rc != 0:
                module.fail_json(msg='Failed to run container', stderr=stderr, rc=rc)
        return True, 'Container created and started'

    if current_state == 'stopped':
        if not module.check_mode:
            rc, _, stderr = run_cli(['start', params['name']])
            if rc != 0:
                module.fail_json(msg='Failed to start container', stderr=stderr, rc=rc)
        return True, 'Container started'

    return False, 'Container already running'


def ensure_stopped(module, params, info, current_state):
    if current_state == 'running':
        if not module.check_mode:
            rc, _, stderr = run_cli(['stop', params['name']])
            if rc != 0:
                module.fail_json(msg='Failed to stop container', stderr=stderr, rc=rc)
        return True, 'Container stopped'

    if current_state == 'absent':
        return False, 'Container does not exist'

    return False, 'Container already stopped'


def ensure_restarted(module, params, info, current_state):
    if current_state == 'absent':
        if not params['image']:
            module.fail_json(msg="Parameter 'image' is required when state is 'restarted' and container does not exist")
        if not module.check_mode:
            rc, _, stderr = run_cli(build_run_args(params))
            if rc != 0:
                module.fail_json(msg='Failed to run container', stderr=stderr, rc=rc)
        return True, 'Container created and started'

    # Image changed → recreate instead of plain restart
    if params['image'] and not image_matches(info, params['image']):
        if not module.check_mode:
            _stop_and_delete(module, params['name'], current_state)
            rc, _, stderr = run_cli(build_run_args(params))
            if rc != 0:
                module.fail_json(msg='Failed to run container', stderr=stderr, rc=rc)
        return True, 'Container recreated with updated image'

    if not module.check_mode:
        if current_state == 'running':
            rc, _, stderr = run_cli(['stop', params['name']])
            if rc != 0:
                module.fail_json(msg='Failed to stop container', stderr=stderr, rc=rc)
        # --rm containers are auto-deleted on stop; must use run instead of start
        if params['remove']:
            rc, _, stderr = run_cli(build_run_args(params))
        else:
            rc, _, stderr = run_cli(['start', params['name']])
        if rc != 0:
            module.fail_json(msg='Failed to start container', stderr=stderr, rc=rc)

    return True, 'Container restarted'


def ensure_present(module, params, info, current_state):
    """Container must exist (created) but need not be running."""
    if current_state != 'absent':
        return False, 'Container already present'

    args_detached = ['run', '-d', '--name', params['name']]
    for port in (params['ports'] or []):
        args_detached += ['-p', port]
    for vol in (params['volumes'] or []):
        args_detached += ['-v', vol]
    for env in (params['env'] or []):
        args_detached += ['-e', env]
    args_detached.append(params['image'])

    if not module.check_mode:
        rc, _, stderr = run_cli(args_detached)
        if rc != 0:
            module.fail_json(msg='Failed to create container', stderr=stderr, rc=rc)
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
        rc, _, stderr = run_cli(['delete', params['name']])
        if rc != 0:
            module.fail_json(msg='Failed to remove container', stderr=stderr, rc=rc)

    return True, 'Container removed'


def main():
    module_args = dict(
        name=dict(type='str', required=True),
        image=dict(type='str', required=False),
        state=dict(type='str', default='started',
                   choices=['started', 'stopped', 'restarted', 'present', 'absent']),
        ports=dict(type='list', elements='str', required=False, default=[]),
        volumes=dict(type='list', elements='str', required=False, default=[]),
        env=dict(type='list', elements='str', required=False, default=[]),
        detach=dict(type='bool', default=True),
        remove=dict(type='bool', default=False),
        cpus=dict(type='str', required=False),
        memory=dict(type='str', required=False),
        user=dict(type='str', required=False),
        command=dict(type='raw', required=False, default=[]),
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    params = module.params

    state = params['state']

    if state == 'present' and not params['image']:
        module.fail_json(msg="Parameter 'image' is required when state is 'present'")

    info = container_inspect(params['name'])
    current_state = container_state(info)

    dispatch = {
        'started':   lambda: ensure_started(module, params, info, current_state),
        'stopped':   lambda: ensure_stopped(module, params, info, current_state),
        'restarted': lambda: ensure_restarted(module, params, info, current_state),
        'present':   lambda: ensure_present(module, params, info, current_state),
        'absent':    lambda: ensure_absent(module, params, info, current_state),
    }

    changed, msg = dispatch[state]()

    module.exit_json(changed=changed, msg=msg, name=params['name'], state=state)


if __name__ == '__main__':
    main()
