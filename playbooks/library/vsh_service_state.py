from ansible.module_utils.basic import AnsibleModule
import yaml
import os

def load_services_file(services_file):
    if not os.path.exists(services_file):
        raise Exception(f"Services file not found: {services_file}. Ensure valet-base role has been run first.")
    try:
        with open(services_file, 'r') as f:
            content = yaml.safe_load(f) or {}
        return content
    except Exception as e:
        raise Exception(f"Failed to load services file {services_file}: {str(e)}")

def save_services_file(services_file, content):
    try:
        with open(services_file, 'w') as f:
            yaml.safe_dump(content, f, default_flow_style=False)
    except Exception as e:
        raise Exception(f"Failed to save services file {services_file}: {str(e)}")

def load_service_definitions(service_definitions_file):
    if not os.path.exists(service_definitions_file):
        raise Exception(f"Service definitions file not found: {service_definitions_file}")
    try:
        with open(service_definitions_file, 'r') as f:
            content = yaml.safe_load(f) or {}
        return content.get('valet_sh_service_definitions', {})
    except Exception as e:
        raise Exception(f"Failed to load service definitions file {service_definitions_file}: {str(e)}")

def main():
    module_args = dict(
        action=dict(type='str', required=True, choices=[
            'add_installed', 'remove_installed', 'set_default',
            'set_enabled', 'set_disabled', 'is_installed'
        ]),
        canonical_names=dict(type='list', required=False, default=[]),
        service_name=dict(type='str', required=False),
        enabled=dict(type='bool', required=False),
        services_file=dict(
            type='str',
            required=False,
            default='/usr/local/valet-sh/etc/services.yml'
        ),
        service_definitions_file=dict(
            type='str',
            required=False,
            default='/usr/local/valet-sh/valet-sh/roles/shared-variables/defaults/main/valet-service-new.yml'
        ),
    )

    result = dict(
        changed=False,
        installed_services=[],
        is_installed=False,
        message=''
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    action = module.params['action']
    canonical_names = module.params['canonical_names']
    if isinstance(canonical_names, str):
        canonical_names = [canonical_names]
    service_name = module.params['service_name']
    service_definitions = load_service_definitions(module.params['service_definitions_file'])
    service_family_name = service_definitions.get(service_name, {}).get('family_name')
    services_file = module.params['services_file']

    if module.check_mode:
        module.exit_json(**result)

    try:
        services_content = load_services_file(services_file)

        if action == 'add_installed':
            for name in canonical_names:
                if name not in services_content['services']['installed']:
                    services_content['services']['installed'][name] = {}
                    result['changed'] = True
            result['message'] = f"Added services: {', '.join(canonical_names)}"

        elif action == 'remove_installed':
            for name in canonical_names:
                if name in services_content['services']['installed']:
                    del services_content['services']['installed'][name]
                    result['changed'] = True
                if name in services_content['services']['states']:
                    del services_content['services']['states'][name]
                    result['changed'] = True
                defaults_to_remove = [k for k, v in services_content['services']['defaults'].items() if v == name]
                for key in defaults_to_remove:
                    del services_content['services']['defaults'][key]
                    result['changed'] = True
            result['message'] = f"Removed services: {', '.join(canonical_names)}"

        elif action == 'set_default':
            if not service_name or not canonical_names:
                module.fail_json(msg="set_default requires service_name and canonical_names")
            canonical_name = canonical_names[0]
            if canonical_name in services_content['services']['installed']:
                target_key = service_family_name if service_family_name else service_name

                current_default = services_content['services']['defaults'].get(target_key)
                if current_default != canonical_name:
                    services_content['services']['defaults'][target_key] = canonical_name
                    result['changed'] = True
                result['message'] = f"Set {canonical_name} as default for {target_key}"
            else:
                module.fail_json(msg=f"Cannot set {canonical_name} as default - not installed")

        elif action == 'set_enabled':
            for name in canonical_names:
                if name in services_content['services']['installed']:
                    current_state = services_content['services']['states'].get(name)
                    if current_state is not True:
                        services_content['services']['states'][name] = True
                        result['changed'] = True
            result['message'] = f"Enabled services: {', '.join(canonical_names)}"

        elif action == 'set_disabled':
            for name in canonical_names:
                if name in services_content['services']['installed']:
                    current_state = services_content['services']['states'].get(name)
                    if current_state is not False:
                        services_content['services']['states'][name] = False
                        result['changed'] = True
            result['message'] = f"Disabled services: {', '.join(canonical_names)}"

        elif action == 'is_installed':
            if canonical_names:
                result['installed_services'] = [name for name in canonical_names if name in services_content['services']['installed']]
                result['is_installed'] = len(result['installed_services']) == len(canonical_names)
                result['message'] = f"Checked {len(canonical_names)} services"

        if result['changed']:
            save_services_file(services_file, services_content)

        module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=f"Error in vsh_service_state: {str(e)}")

if __name__ == '__main__':
    main()
