#!/usr/bin/python
# -*- coding: utf-8 -*-

from ansible.module_utils.basic import AnsibleModule
import subprocess
import json


def run_cli(args):
    cmd = ['container'] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def parse_image_ref(name, tag):
    """
    Build a canonical image reference.
    If the last path segment already contains a colon (tag embedded,
    e.g. 'docker.io/nginx:1.25'), use name as-is and ignore tag.
    """
    last_segment = name.split('/')[-1]
    if ':' in last_segment:
        return name
    return '%s:%s' % (name, tag) if tag else name


def image_id(ref):
    rc, stdout, _ = run_cli(['image', 'inspect', ref])
    if rc != 0:
        return None
    try:
        data = json.loads(stdout)
        if isinstance(data, list):
            data = data[0] if data else {}
        return data.get('Id') or data.get('id') or data.get('Digest') or data.get('digest')
    except (ValueError, KeyError):
        pass
    return stdout


def image_exists(ref):
    return image_id(ref) is not None


def main():
    module_args = dict(
        name=dict(type='str', required=True),
        tag=dict(type='str', required=False, default='latest'),
        state=dict(type='str', default='present', choices=['present', 'absent']),
        # pull=true forces a fresh pull even when the image is already present,
        # matching the behaviour of the community.general.podman_image module.
        pull=dict(type='bool', default=False),
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    params = module.params

    ref = parse_image_ref(params['name'], params['tag'])
    state = params['state']
    force_pull = params['pull']

    exists = image_exists(ref)

    if state == 'present':
        if exists and not force_pull:
            module.exit_json(changed=False, msg='Image already present', image=ref)

        id_before = image_id(ref)

        if module.check_mode:
            # cannot know without pulling whether the remote image changed
            changed = not exists or force_pull
            msg = 'Image pulled' if not exists else 'Image would be refreshed (pull=true)'
            module.exit_json(changed=changed, msg=msg, image=ref)

        rc, stdout, stderr = run_cli(['image', 'pull', ref])
        if rc != 0:
            module.fail_json(msg='Failed to pull image', image=ref, stderr=stderr, rc=rc)

        id_after = image_id(ref)
        changed = id_before != id_after
        if not exists:
            msg = 'Image pulled'
        elif changed:
            msg = 'Image updated'
        else:
            msg = 'Image already up to date'
        module.exit_json(changed=changed, msg=msg, image=ref)

    else:  # absent
        if not exists:
            module.exit_json(changed=False, msg='Image already absent', image=ref)
        if not module.check_mode:
            rc, stdout, stderr = run_cli(['image', 'delete', ref])
            if rc != 0:
                module.fail_json(msg='Failed to remove image', image=ref, stderr=stderr, rc=rc)
        module.exit_json(changed=True, msg='Image removed', image=ref)


if __name__ == '__main__':
    main()
