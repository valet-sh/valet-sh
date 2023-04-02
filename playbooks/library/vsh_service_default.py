from ansible.module_utils.basic import AnsibleModule
import yaml

def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(required=True, type='str'),
            family=dict(required=True, type='str')
        )
    )
    name = module.params.get('name')
    family = module.params.get('family')

    with open('/usr/local/valet-sh/etc/defaults.yml', 'r') as file:
        defaults = yaml.safe_load(file)

    original = dict(defaults)
    defaults[family] = name

    with open('/usr/local/valet-sh/etc/defaults.yml', 'w') as file:
        yaml.safe_dump(defaults, file)

    if original == defaults:
        changed = False
    else:
        changed = True

    module.exit_json(changed=changed)

if __name__ == '__main__':
    main()
