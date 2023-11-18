from ansible.module_utils.basic import AnsibleModule
import yaml

def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(required=False, type='str')
        )
    )
    name = module.params.get('name')

    with open('/usr/local/valet-sh/etc/services.yml', 'r') as file:
        services = yaml.safe_load(file)

    if not name:
        module.exit_json(changed=False, result=services)

    if name not in services:
        result = {
            "state": "absent"
        }
        module.exit_json(changed=False, result=result)
    else:
        module.exit_json(changed=False, result=services[name])

if __name__ == '__main__':
    main()
