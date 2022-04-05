DOCUMENTATION = '''
---
module: vsh-table
short_description: This is a valet-sh module for table output on cli.
description:
    - Table ansible module
    - Provides possibility to output formated tables on cli via valet-sh
author: "Johann Zelger <j.zelger@techdivision.com>"
options:
    headers:
        description:
          - A list of header colums
    rows:
        description:
          - a list of rows which also are lists
usage:
    - vsh-table:
      headers: ['col1', 'col2', 'col3']
      rows: [
        ['row1val1', 'row1val2', 'row1val3'],
        ['row2val1', 'row2val2', 'row2val3'],
        ['row3val1', 'row3val2', 'row3val3']
      ]
requirements:
  - "python >= 2.6"
  - "beautifultable" >= "0.5.3"
'''

from ansible.module_utils.basic import AnsibleModule
from beautifultable import BeautifulTable

def main():

    module = AnsibleModule(
        argument_spec=dict(
            headers=dict(required=True, type='list'),
            rows=dict(required=True, type='list')
        )
    )

    headers = module.params.get('headers')
    rows = module.params.get('rows')

    table = BeautifulTable(max_width=120)
    table.column_headers = headers
    
    for row in rows:
        if (len(row) != len(headers)):
            module.fail_json(msg='row list count does not equal headers list count %s' % row)
        table.append_row(row)
    
    module.exit_json(changed=True, vsh_stdout=str(table))

if __name__ == '__main__':
    main()