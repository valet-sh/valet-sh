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
        state=dict(type='str', required=False, choices=['present', 'absent']),
        scope=dict(type='str', required=False, choices=['essential', 'optional']),
        name=dict(type='raw', required=False, default=None),
        bundle_etc_file=dict(type='str', default='/usr/local/valet-sh/etc/bundles.yml'),
        bundle_role_definitions_file=dict(
            type='str',
            default='/usr/local/valet-sh/valet-sh/roles/shared-variables/defaults/main/valet-bundles.yml'
        ),
    )

    result = dict(changed=False, kinds=[], message='')
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    params = module.params

    names = params.get('name')
    if isinstance(names, str):
        names = [names]
    elif isinstance(names, list) and len(names) == 0:
        names = None

    scope = params.get('scope')
    state = params.get('state')

    try:
        candidate_kinds = []

        if scope:
            bundle_definitions_content = load_bundle_file(params['bundle_role_definitions_file'])
            for section in ['services', 'packages']:
                for name, definition in bundle_definitions_content.get('valet_sh_bundle_definitions', {}).get(section, {}).items():
                    if definition.get('kind') == scope:
                        candidate_kinds.append(name)

        if names:
            if candidate_kinds:
                candidate_kinds = [n for n in candidate_kinds if n in names]
            else:
                candidate_kinds = list(names)

        resolved_kinds = candidate_kinds

        if state:
            bundle_file_content = load_bundle_file(params['bundle_etc_file'])

            etc_all = []
            etc_installed = []
            for section in ['services', 'packages']:
                section_data = bundle_file_content.get('bundles', {}).get(section, {})
                installed = section_data.get('installed', {})
                for name in installed.keys():
                    etc_all.append(name)
                    etc_installed.append(name)
                states = section_data.get('states', {})
                for name in states.keys():
                    if name not in etc_all:
                        etc_all.append(name)

            if not resolved_kinds:
                resolved_kinds = etc_all

            if state == 'present':
                resolved_kinds = [n for n in resolved_kinds if n in etc_installed]
            elif state == 'absent':
                resolved_kinds = [n for n in resolved_kinds if n not in etc_installed]

        print(f"Result kinds: {resolved_kinds}")
        result['kinds'] = resolved_kinds
        module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=f"Error in vsh_bundle_state: {str(e)}")

if __name__ == '__main__':
    main()
