from ansible.module_utils.basic import AnsibleModule
import yaml


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(required=True, type='str'),
            state=dict(required=False, type='str'),
            package_type=dict(required=False, type='str'),
            enabled=dict(required=False, type='bool')
        )
    )
    name = module.params.get('name')
    state = module.params.get('state')
    enabled = module.params.get('enabled')
    package_type = module.params.get('package_type')

    with open('/usr/local/valet-sh/etc/services.yml', 'r') as file:
        services = yaml.safe_load(file)

    original = dict(services)

    if name in services:
        if state is not None:
            services[name]["state"] = state
        if enabled is not None:
            services[name]["enabled"] = enabled
        if package_type is not None:
            services[name]["package_type"] = package_type

    if name not in services:
        result = {}
        if state is not None:
            result["state"] = state
        if enabled is not None:
            result["enabled"] = enabled
        if package_type is not None:
            result["package_type"] = package_type

        services[name] = result

    with open('/usr/local/valet-sh/etc/services.yml', 'w') as file:
        yaml.safe_dump(services, file)

    if original == services:
        changed = False
    else:
        changed = True

    module.exit_json(changed=changed)


if __name__ == '__main__':
    main()
