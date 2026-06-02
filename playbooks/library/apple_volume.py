#!/usr/bin/python
# -*- coding: utf-8 -*-

from ansible.module_utils.basic import AnsibleModule
import subprocess


def run_cli(args):
    cmd = ['container'] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def volume_exists(name):
    rc, _stdout, _stderr = run_cli(['volume', 'inspect', name])
    return rc == 0


def main():
    module_args = dict(
        name=dict(type='str', required=True),
        state=dict(type='str', default='present', choices=['present', 'absent']),
        options=dict(type='list', elements='str', required=False, default=[]),
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    params = module.params

    name = params['name']
    state = params['state']

    exists = volume_exists(name)

    if state == 'present':
        if exists:
            module.exit_json(changed=False, msg='Volume already exists', name=name)
        if not module.check_mode:
            args = ['volume', 'create']
            for opt in (params['options'] or []):
                args += ['--opt', opt]
            args.append(name)
            rc, stdout, stderr = run_cli(args)
            if rc != 0:
                module.fail_json(msg='Failed to create volume', stderr=stderr, rc=rc)
        module.exit_json(changed=True, msg='Volume created', name=name)

    else:  # absent
        if not exists:
            module.exit_json(changed=False, msg='Volume already absent', name=name)
        if not module.check_mode:
            rc, stdout, stderr = run_cli(['volume', 'delete', name])
            if rc != 0:
                module.fail_json(msg='Failed to remove volume', stderr=stderr, rc=rc)
        module.exit_json(changed=True, msg='Volume removed', name=name)


if __name__ == '__main__':
    main()
