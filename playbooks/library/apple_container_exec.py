#!/usr/bin/python
# -*- coding: utf-8 -*-

from ansible.module_utils.basic import AnsibleModule
import subprocess
import json


def run_cli(args):
    cmd = ['container'] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def container_is_running(name):
    rc, stdout, stderr = run_cli(['inspect', name])
    if rc != 0:
        return False
    try:
        data = json.loads(stdout)
        if isinstance(data, list):
            data = data[0] if data else {}
        status = ''
        if 'State' in data:
            status = data['State'].get('Status', '').lower()
        elif 'status' in data:
            status = data['status'].lower()
        return status == 'running'
    except (ValueError, KeyError):
        return False


def main():
    module_args = dict(
        name=dict(type='str', required=True),
        command=dict(type='str', required=False),
        argv=dict(type='list', elements='str', required=False, default=[]),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
        mutually_exclusive=[['command', 'argv']],
        required_one_of=[['command', 'argv']],
    )
    params = module.params

    name = params['name']

    if not container_is_running(name):
        module.fail_json(msg="Container '%s' is not running" % name, name=name)

    if params['argv']:
        cmd_args = params['argv']
    else:
        cmd_args = params['command'].split()

    if module.check_mode:
        module.exit_json(changed=True, msg='Would execute command (check mode)', name=name,
                         cmd=cmd_args, stdout='', stderr='', rc=0)

    rc, stdout, stderr = run_cli(['exec', name] + cmd_args)

    if rc != 0:
        module.fail_json(
            msg='Command failed in container',
            name=name,
            cmd=cmd_args,
            stdout=stdout,
            stderr=stderr,
            rc=rc,
        )

    module.exit_json(
        changed=True,
        msg='Command executed successfully',
        name=name,
        cmd=cmd_args,
        stdout=stdout,
        stderr=stderr,
        rc=rc,
    )


if __name__ == '__main__':
    main()