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

def normalize_service_input(service_input):
    return re.sub(r'[.\s]', '', service_input).lower()

def parse_service_input(service_input):
    normalized = normalize_service_input(service_input)

    match = re.match(r'^([a-z]+)(\d+.*)?$', normalized)
    if match:
        service_name = match.group(1)
        version_raw = match.group(2)
        return service_name, version_raw

    return normalized, None

def load_service_definitions(definitions_file):
    if not os.path.exists(definitions_file):
        raise Exception(f"Service definitions file not found: {definitions_file}")

    definitions_data = load_yaml_file(definitions_file)
    return definitions_data.get('valet_sh_service_definitions', {})

def load_service_config(service_name, version, services_dir):
    config_file = f"{services_dir}/{service_name}/{version}.yml"

    if not os.path.exists(config_file):
        return None

    return load_yaml_file(config_file)

def resolve_service_version(service_name, requested_version, service_meta):
    available_versions = service_meta.get('versions', [])
    default_version = service_meta.get('default_version')

    if not available_versions:
        if default_version:
            return default_version
        else:
            return 'default'

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

def build_service_config(service_name, version, service_meta, detailed_config, current_os):
    version_compact = version.replace('.', '') if version else ''

    if version and version.lower() not in ['latest', 'default']:
        canonical = f"{service_name}{version_compact}"
    else:
        canonical = service_name

    config = {
        'service_name': service_name,
        'role_name': service_meta.get('role_name', service_name),
        'canonical': canonical,
        'display_name': service_meta.get('display_name', service_name),
        'defaultable': service_meta.get('defaultable', False),
        'group': service_meta.get('group'),
        'matched_pattern': 'definitions_lookup'
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

def resolve_service(service_input, definitions, services_dir, current_os):
    service_name, requested_version = parse_service_input(service_input)

    if service_name not in definitions:
        return None, f"Service '{service_name}' not found in definitions"

    service_meta = definitions[service_name]

    version = resolve_service_version(service_name, requested_version, service_meta)
    if not version:
        available = service_meta.get('versions', [])
        return None, f"Version '{requested_version}' not available for '{service_name}'. Available: {available}"

    detailed_config = load_service_config(service_name, version, services_dir)
    config = build_service_config(service_name, version, service_meta, detailed_config, current_os)

    return config, None

def main():
    module_args = dict(
        services=dict(type='list', required=True),
        definitions_file=dict(
            type='str',
            required=False,
            default='/usr/local/valet-sh/valet-sh/roles/shared-variables/defaults/main/valet-service-new.yml'
        ),
        services_dir=dict(
            type='str',
            required=False,
            default='/usr/local/valet-sh/valet-sh/roles/shared-variables/defaults/main/services'
        ),
        current_os=dict(type='str', required=False, default='ubuntu')
    )

    result = dict(
        changed=False,
        services=[],
        errors=[]
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    services_input = module.params['services']
    definitions_file = module.params['definitions_file']
    services_dir = module.params['services_dir']
    current_os = module.params['current_os']

    if len(services_input) == 1 and (',' in services_input[0] or ' ' in services_input[0]):
        service_parts = []
        for part in services_input[0].split(','):
            service_parts.extend(part.split())
        services_input = [s.strip() for s in service_parts if s.strip()]

    try:
        definitions = load_service_definitions(definitions_file)

        for service_input in services_input:
            service_input = service_input.strip()

            config, error = resolve_service(service_input, definitions, services_dir, current_os)

            if config:
                result['services'].append(config)
            else:
                result['errors'].append({
                    'service_input': service_input,
                    'error': error
                })


        if result['errors']:
            error_details = []
            for error in result['errors']:
                error_details.append(f"{error['error']}")

            detailed_msg = f"Failed to resolve services:\n" + "\n".join(error_details)
            module.fail_json(msg=detailed_msg, **result)

        module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=f"Error processing services: {str(e)}")


if __name__ == '__main__':
    main()
