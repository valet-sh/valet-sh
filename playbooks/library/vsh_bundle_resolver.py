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

def normalize_input(input):
    return re.sub(r'[.\s]', '', input).lower()

def parse_input(input):
    normalized = normalize_input(input)

    match = re.match(r'^([a-z]+)(\d+.*)?$', normalized)
    if match:
        name = match.group(1)
        version_raw = match.group(2)
        return name, version_raw

    return normalized, None

def resolve_version(requested_version, bundle_meta):
    available_versions = bundle_meta.get('versions', [])
    default_version = bundle_meta.get('default_version')

    if not available_versions:
        return default_version or 'default'

    if not requested_version:
        if default_version:
            return default_version
        elif available_versions:
            return available_versions[0]
        else:
            return None

    if requested_version in available_versions:
        return requested_version

    requested_compact = requested_version.replace('.', '')
    for available_version in available_versions:
        available_compact = available_version.replace('.', '')
        if requested_compact == available_compact:
            return available_version

    return None

def build_config(name, version, bundle_meta, detailed_config, current_os):
    version_compact = version.replace('.', '') if version else ''

    if version and version.lower() not in ['latest', 'default']:
        canonical = f"{name}{version_compact}"
    else:
        canonical = name

    config = {
        'name': name,
        'role_name': bundle_meta.get('role_name', name),
        'canonical': canonical,
        'display_name': bundle_meta.get('display_name', name),
        'enable_allowed': bundle_meta.get('enable_allowed', False),
        'family_name': bundle_meta.get('family_name'),
        'kind': bundle_meta.get('kind', 'optional'),
        'type': bundle_meta.get('type', 'service'),
    }

    if version:
        config['version'] = version
        config['version_compact'] = version_compact

    if detailed_config:
        service_config = detailed_config.get('service', {})
        if service_config:
            resolved_service = {}
            for key, value in service_config.items():
                if isinstance(value, dict) and current_os in value:
                    resolved_value = value[current_os]
                else:
                    resolved_value = value

                resolved_service[key] = resolved_value
            config['service'] = resolved_service

        for key, value in detailed_config.items():
            if key != 'service':
                config[key] = value

    return config

def resolve_bundle_item(input, definitions, config_dir, current_os):
    name, requested_version = parse_input(input)

    if name not in definitions:
        return None, f"'{name}' not found in definitions"

    bundle_meta = definitions[name]
    version = resolve_version(requested_version, bundle_meta)

    if not version:
        available = bundle_meta.get('versions', [])
        return None, f"Version '{requested_version}' not available for '{name}'. Available: {available}"

    config_file = f"{config_dir}/{name}/{version}.yml"
    detailed_config = load_yaml_file(config_file) if os.path.exists(config_file) else None
    config = build_config(name, version, bundle_meta, detailed_config, current_os)

    return config, None

def main():
    module_args = dict(
        name=dict(type='list', required=True),
        definitions_file=dict(
            type='str',
            required=False,
            default='/usr/local/valet-sh/valet-sh/roles/shared-variables/defaults/main/valet-bundles.yml'
        ),
        config_dir=dict(
            type='str',
            required=False,
            default='/usr/local/valet-sh/valet-sh/roles/shared-variables/defaults/main/bundles'
        ),
        current_os=dict(type='str', required=False, default='ubuntu'),
        custom_fact=dict(type='str', required=False, default=None)
    )

    result = {
        "changed": False,
        "services":[],
        "packages": [],
        "errors": []
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    params = module.params
    custom_fact = params['custom_fact']

    item_input = params['name']

    if len(item_input) == 1 and (',' in item_input[0] or ' ' in item_input[0]):
        service_parts = []
        for part in item_input[0].split(','):
            service_parts.extend(part.split())
        item_input = [s.strip() for s in service_parts if s.strip()]

    try:
        definitions_data = load_yaml_file(params['definitions_file'])
        bundle_definitions = definitions_data.get('valet_sh_bundle_definitions', {})

        definitions = {}
        for bundle_type, items in bundle_definitions.items():
            if isinstance(items, dict):
                definitions.update(items)

        for input in item_input:
            input = input.strip()
            if not input: continue

            config, error = resolve_bundle_item(input, definitions, params['config_dir'], params['current_os'])

            if config:
                if config.get('type') == 'service':
                    result['services'].append(config)
                elif config.get('type') == 'package':
                    result['packages'].append(config)
            else:
                result['errors'].append(error)

        if custom_fact:
            result['ansible_facts'] = {custom_fact: {k: v for k, v in result.items() if k != 'ansible_facts'}}

        if result['errors']:
            module.fail_json(msg="Validation failed: " + ", ".join(result['errors']), **result)

        module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=f"Error processing services: {str(e)}")

if __name__ == '__main__':
    main()
