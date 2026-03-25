from ansible.module_utils.basic import AnsibleModule
import yaml
import os

def load_bundle_file(bundle_file):
    if not os.path.exists(bundle_file):
        raise Exception(f"Bundle file not found: {bundle_file}. Ensure valet-base role has been run first.")
    try:
        with open(bundle_file, 'r') as f:
            content = yaml.safe_load(f) or {}
        return content
    except Exception as e:
        raise Exception(f"Failed to load services file {bundle_file}: {str(e)}")

def main():
    module_args = dict(
        name=dict(type='raw', required=True),
        bundle_etc_file=dict(type='str', default='/usr/local/valet-sh/etc/bundles.yml'),
    )

    result = dict(changed=False, states={}, message='')
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    params = module.params

    names = params.get('name')
    if isinstance(names, str):
        names = [names]
    elif not isinstance(names, list) or len(names) == 0:
        module.fail_json(msg="'name' must be a non-empty string or list")

    try:
        bundle_file_content = load_bundle_file(params['bundle_etc_file'])
        bundle_states = bundle_file_content.get('bundles', {}).get('services', {}).get('states', {})

        resolved = {}
        for name in names:
            if name not in bundle_states:
                resolved[name] = 'unknown'
            else:
                resolved[name] = 'enabled' if bundle_states[name] else 'disabled'

        result['states'] = resolved
        if len(names) == 1:
            result['state'] = resolved[names[0]]

        module.exit_json(**result)
    except Exception as e:
        module.fail_json(msg=f"Error in vsh_bundle_service_state_info: {str(e)}")

if __name__ == '__main__':
    main()
