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

def save_bundle_file(bundle_file, content):
    try:
        with open(bundle_file, 'w') as f:
            yaml.safe_dump(content, f, default_flow_style=False)
    except Exception as e:
        raise Exception(f"Failed to save services file {bundle_file}: {str(e)}")

def find_definition(name, all_definitions):
    if name in all_definitions:
        return all_definitions[name]
    for key, definition in all_definitions.items():
        if name and name.startswith(key):
            return definition
    return {}

def find_definition_key(name, all_definitions):
    if name in all_definitions:
        return name
    for key in all_definitions.keys():
        if name and name.startswith(key):
            return key
    return None

def main():
    module_args = dict(
        action=dict(type='str', required=True, choices=[
            'installed', 'uninstalled', 'default',
            'enabled', 'disabled', 'initialize_empty'
        ]),
        canonical_names=dict(type='list', required=False, default=[]),
        name=dict(type='str', required=False),

        bundle_file=dict(type='str', default='/usr/local/valet-sh/etc/bundles.yml'),
        bundle_definitions_file=dict(
            type='str',
            default='/usr/local/valet-sh/valet-sh/roles/shared-variables/defaults/main/valet-bundles.yml'
        ),
    )

    result = dict(changed=False, installed_services=[], message='')
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    params = module.params

    try:
        bundle_file_content = load_bundle_file(params['bundle_file'])
        bundle_definitions_content = load_bundle_file(params['bundle_definitions_file'])

        all_definitions = {}
        for section in ['services', 'packages']:
            for name, definition in bundle_definitions_content.get('valet_sh_bundle_definitions', {}).get(section, {}).items():
                all_definitions[name] = definition

        names = params['canonical_names']
        if isinstance(names, str):
            names = [n.strip() for n in names.split(',') if n.strip()]
        elif not isinstance(names, list):
            names = [names] if names else []

        if not names and params['name']:
            names = [params['name']]


        lookup_name = params['name'] if params['name'] else (names[0] if names else None)
        item_type = find_definition(lookup_name, all_definitions).get('type', 'service')
        b_type = 'packages' if item_type == 'package' else 'services'

        target = bundle_file_content['bundles'].setdefault(b_type, {'installed': {}, 'states': {}, 'defaults': {}})
        family_name = find_definition(lookup_name, all_definitions).get('family_name')

        if module.check_mode:
            module.exit_json(**result)

        if params['action'] == 'installed':
            for name in names:
                if name not in target['installed']:
                    target['installed'][name] = {}
                    result['changed'] = True
            result['message'] = f"Added {b_type}: {', '.join(names)}"

        elif params['action'] == 'uninstalled':
            for name in names:
                if name in target['installed']:
                    del target['installed'][name]
                    result['changed'] = True

                if name in target['states']:
                    del target['states'][name]
                    result['changed'] = True

                keys_to_fix = [k for k, v in target['defaults'].items() if v == name]

                for key in keys_to_fix:
                    del target['defaults'][key]
                    result['changed'] = True

                    candidates = [
                        s for s in target['installed'].keys()
                        if find_definition(s, all_definitions).get('family_name') == key
                        or find_definition_key(s, all_definitions) == key
                    ]
                    if candidates:
                        target['defaults'][key] = sorted(candidates)[-1]

            result['message'] = f"Removed {b_type}: {', '.join(names)} and updated defaults accordingly"



        elif params['action'] == 'default':
            if not params['name'] or not names:
                module.fail_json(msg="default requires name and canonical_names")
            canonical_name = names[0]
            if canonical_name in target['installed']:
                target_key = family_name if family_name else params['name']

                current_default = target['defaults'].get(target_key)
                if current_default != canonical_name:
                    target['defaults'][target_key] = canonical_name
                    result['changed'] = True
                result['message'] = f"Set {canonical_name} as default for {target_key}"
            else:
                module.fail_json(msg=f"Cannot set {canonical_name} as default - not installed")

        elif params['action'] in ['enabled', 'disabled']:
            for name in names:
                if name in target['installed']:
                    desired_state = True if params['action'] == 'enabled' else False
                    current_state = target['states'].get(name)
                    if current_state != desired_state:
                        target['states'][name] = desired_state
                        result['changed'] = True
            state_str = 'Enabled' if params['action'] == 'enabled' else 'Disabled'
            result['message'] = f"{state_str} {b_type}: {', '.join(names)}"

        elif params['action'] == 'initialize_empty':
            for name in names:
                name_type = find_definition(name, all_definitions).get('type', 'service')
                name_section = 'packages' if name_type == 'package' else 'services'
                name_target = bundle_file_content['bundles'].setdefault(name_section, {'installed': {}, 'states': {}, 'defaults': {}})
                if name not in name_target.get('states', {}):
                    name_target.setdefault('states', {})[name] = True
                    result['changed'] = True

        if result['changed']:
            save_bundle_file(params['bundle_file'], bundle_file_content)

        module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=f"Error in vsh_bundle_state: {str(e)}")

if __name__ == '__main__':
    main()
