from ansible.module_utils.basic import AnsibleModule
import yaml
import re
import os

def load_yaml_file(file_path):
    try:
        with open(file_path, 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        raise Exception(f"Failed to load {file_path}: {str(e)}")

def main():
    module_args = dict(
        bundle_file =dict(
            type='str',
            required=False,
            default='/usr/local/valet-sh/etc/bundles.yml'
        ),
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    bundles_path = module.params['bundle_file']

    table_rows = []

    try:
        bundle_contents = load_yaml_file(bundles_path)
        bundle_content = bundle_contents.get('bundles', {})

        for bundle_key in ['services', 'packages']:
            bundle = bundle_content.get(bundle_key, {})

            installed_item = bundle.get('installed', {})
            states = bundle.get('states', {})
            defaults = bundle.get('defaults', {})

            active_defaults = defaults.values()
            row_type = 'service' if bundle_key == 'services' else 'package'

            for name in installed_item:

                is_default = '1' if name in active_defaults else '-'
                table_rows.append([
                    row_type,
                    name,
                    is_default,
                    states.get(name, '-')
                ])


        module.exit_json(changed=False, table_rows=table_rows)

    except Exception as e:
        module.fail_json(msg=f"Error: {str(e)}")

if __name__ == '__main__':
    main()
