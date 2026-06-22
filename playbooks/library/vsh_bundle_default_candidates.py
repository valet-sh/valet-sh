from ansible.module_utils.basic import AnsibleModule
import yaml
import os

def load_yaml_file(path):
    if not os.path.exists(path):
        raise Exception(f"File not found: {path}")
    with open(path, 'r') as f:
        return yaml.safe_load(f) or {}

def main():
    module_args = dict(
        services=dict(type='list', required=True),
        bundle_etc_file=dict(type='str', default='/usr/local/valet-sh/etc/bundles.yml'),
        bundle_role_definitions_file=dict(
            type='str',
            default='/usr/local/valet-sh/valet-sh/roles/shared-variables/defaults/main/valet-bundles.yml'
        ),
    )

    result = dict(changed=False, canonical_names=[])
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    params = module.params

    try:
        state = load_yaml_file(params['bundle_etc_file'])
        definitions_data = load_yaml_file(params['bundle_role_definitions_file'])
        all_definitions = definitions_data.get('valet_sh_bundle_definitions', {})

        canonical_names = []
        claimed_families = set()

        # Enforce all currently configured defaults (ensures system state matches bundles.yml,
        # e.g. PHP CLI alternatives that Ubuntu resets on package install)
        for section in ['services', 'packages']:
            section_state = state.get('bundles', {}).get(section, {})
            for family_key, canonical in section_state.get('defaults', {}).items():
                if canonical not in canonical_names:
                    canonical_names.append(canonical)
                claimed_families.add((section, family_key))

        # For newly installed services: if their family has no default yet and no other
        # service of that family is installed, add them as candidates (first install case)
        for service in params['services']:
            name = service.get('name')
            canonical = service.get('canonical')
            svc_type = service.get('type', 'service')
            family_name = service.get('family_name')
            section = svc_type + 's'
            definition = all_definitions.get(section, {}).get(name, {})
            if len(definition.get('versions', [])) <= 1:
                continue
            family_key = family_name if family_name else name
            section_state = state.get('bundles', {}).get(section, {})
            defaults = section_state.get('defaults', {})

            if family_key in defaults:
                continue

            family_id = (section, family_key)
            if family_id in claimed_families:
                continue

            if canonical not in canonical_names:
                canonical_names.append(canonical)
            claimed_families.add(family_id)

        result['canonical_names'] = canonical_names
        module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=f"Error in vsh_bundle_default_candidates: {str(e)}")

if __name__ == '__main__':
    main()
