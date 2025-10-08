DOCUMENTATION = '''
---
module: vsh-links-stat
short_description: 
author: "DevOps <devops@techdivision.com>"
'''

from ansible.module_utils.basic import AnsibleModule
import os

def main():

    module = AnsibleModule(
        argument_spec=dict(
            links=dict(required=True, type='list'),
        )
    )

    links = module.params.get("links")

    for link in links:
        if not os.path.isdir(link['path']):
           link['pathState'] = False

    module.exit_json(changed=True, links=links)

if __name__ == '__main__':
    main()