from ansible.module_utils.basic import AnsibleModule
import yaml

def main():
    module = AnsibleModule(
        argument_spec=dict(
            family=dict(required=False, type='str')
        )
    )
    family = module.params.get('family')

    with open('/usr/local/valet-sh/etc/defaults.yml', 'r') as file:
        defaults = yaml.safe_load(file)

    if not family:
        module.exit_json(changed=False, result=defaults)

    if family not in defaults:
        result = {
            "state": "absent"
        }
        module.exit_json(changed=False, result=result)
    else:
        module.exit_json(changed=False, result=defaults[family])

if __name__ == '__main__':
    main()
