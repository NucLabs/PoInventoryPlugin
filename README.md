# Ib_pf_ms_bhr Inv_plugins Collection

This repository contains the `ib_pf_ms_bhr.inv_plugins` Ansible Collection.

## MSSQL Dynamic Inventory Plugin

This collection includes a dynamic inventory plugin that retrieves hosts from a Microsoft SQL Server database using Kerberos authentication.

### Features

- Queries MSSQL database for host inventory
- Combines `ComputerName` and `DomainName` fields to create FQDNs
- All other query columns become host variables
- Supports Kerberos (default) and SQL Server authentication
- Supports constructed features (groups, keyed_groups, compose)
- Caching support to reduce database load

### Requirements

- Python library: `pymssql`
- For Kerberos authentication: FreeTDS compiled with Kerberos support
- Valid Kerberos ticket (obtain via `kinit`)

### Quick Start

1. Install the collection and dependencies:

```bash
ansible-galaxy collection install ib_pf_ms_bhr.inv_plugins
pip install pymssql
```

2. Create an inventory file (e.g., `inventory.mssql.yml`):

```yaml
---
plugin: ib_pf_ms_bhr.inv_plugins.mssql
host: sqlserver.domain.com
database: inventory_db
query: |
  SELECT ComputerName, DomainName, os_type, environment
  FROM servers
  WHERE active = 1
```

3. Obtain a Kerberos ticket:

```bash
kinit your_username@YOUR.DOMAIN.COM
```

4. Test the inventory:

```bash
# List all hosts as JSON
ansible-inventory -i inventory.mssql.yml --list

# Show inventory in YAML format
ansible-inventory -i inventory.mssql.yml --list --yaml

# Display a graph of the inventory
ansible-inventory -i inventory.mssql.yml --graph

# Show variables for a specific host
ansible-inventory -i inventory.mssql.yml --host server01.domain.com

# Verify connectivity to all hosts
ansible -i inventory.mssql.yml all -m ping
```

### Testing with Verbose Output

For troubleshooting, use verbose flags to see more details:

```bash
# Basic verbose output
ansible-inventory -i inventory.mssql.yml --list -v

# More verbose (shows connection details)
ansible-inventory -i inventory.mssql.yml --list -vvv

# Maximum verbosity
ansible-inventory -i inventory.mssql.yml --list -vvvv
```

### Example with Groups

```yaml
---
plugin: ib_pf_ms_bhr.inv_plugins.mssql
host: sqlserver.domain.com
database: cmdb
query: |
  SELECT ComputerName, DomainName, os_type, environment, datacenter
  FROM servers
  WHERE active = 1

# Optional: Add a prefix to all host variables to avoid naming collisions
# when combining multiple inventory sources (default: empty string)
var_prefix: "mssql_"

# Create groups based on variable values
keyed_groups:
  - prefix: env
    key: environment
  - prefix: os
    key: os_type

# Create groups based on conditions
groups:
  linux: os_type == 'Linux'
  windows: os_type == 'Windows'
  production: environment == 'prod'

# Create additional variables
compose:
  ansible_host: inventory_hostname
```

Test grouped inventory:

```bash
# Show the group structure
ansible-inventory -i inventory.mssql.yml --graph

# List hosts in a specific group
ansible-inventory -i inventory.mssql.yml --graph --vars env_prod
```

For full documentation, see `ansible-doc -t inventory ib_pf_ms_bhr.inv_plugins.mssql`.

## REST API Dynamic Inventory Plugin

The collection also includes a dynamic inventory plugin that retrieves hosts from a REST API endpoint.

### Features

- Queries any REST API returning JSON data
- Combines `ComputerName` and `DomainName` fields to create FQDNs
- All other fields in the JSON response become host variables
- Supports no authentication or Bearer token authentication
- Configurable variable prefix to avoid naming collisions
- Supports constructed features (groups, keyed_groups, compose)
- Caching support

### Requirements

- Python library: `requests`

### Quick Start

1. Install the collection and dependencies:

```bash
ansible-galaxy collection install ib_pf_ms_bhr.inv_plugins
pip install requests
```

2. Create an inventory file (e.g., `inventory.restapi.yml`):

```yaml
---
plugin: ib_pf_ms_bhr.inv_plugins.restapi
url: http://api.example.com/servers

# Optional: Add a prefix to all host variables (default: empty string)
var_prefix: "restapi_"

# Optional: Bearer token authentication
# auth_method: bearer
# bearer_token: "{{ lookup('env', 'API_TOKEN') }}"
```

3. Test the inventory:

```bash
# List all hosts as JSON
ansible-inventory -i inventory.restapi.yml --list

# Show inventory in YAML format  
ansible-inventory -i inventory.restapi.yml --list --yaml
```

For full documentation, see `ansible-doc -t inventory ib_pf_ms_bhr.inv_plugins.restapi`.

<!--start requires_ansible-->
<!--end requires_ansible-->

## External requirements

Some modules and plugins require external libraries. Please check the
requirements for each plugin or module you use in the documentation to find out
which requirements are needed.

## Included content

<!--start collection content-->
<!--end collection content-->

## Using this collection

```bash
    ansible-galaxy collection install ib_pf_ms_bhr.inv_plugins
```

You can also include it in a `requirements.yml` file and install it via
`ansible-galaxy collection install -r requirements.yml` using the format:

```yaml
collections:
  - name: ib_pf_ms_bhr.inv_plugins
```

To upgrade the collection to the latest available version, run the following
command:

```bash
ansible-galaxy collection install ib_pf_ms_bhr.inv_plugins --upgrade
```

You can also install a specific version of the collection, for example, if you
need to downgrade when something is broken in the latest version (please report
an issue in this repository). Use the following syntax where `X.Y.Z` can be any
[available version](https://galaxy.ansible.com/ib_pf_ms_bhr/inv_plugins):

```bash
ansible-galaxy collection install ib_pf_ms_bhr.inv_plugins:==X.Y.Z
```

See
[Ansible Using Collections](https://docs.ansible.com/ansible/latest/user_guide/collections_using.html)
for more details.

## Release notes

See the
[changelog](https://github.com/ansible-collections/ib_pf_ms_bhr.inv_plugins/tree/main/CHANGELOG.rst).

## Roadmap

<!-- Optional. Include the roadmap for this collection, and the proposed release/versioning strategy so users can anticipate the upgrade/update cycle. -->

## More information

<!-- List out where the user can find additional information, such as working group meeting times, slack/matrix channels, or documentation for the product this collection automates. At a minimum, link to: -->

- [Ansible collection development forum](https://forum.ansible.com/c/project/collection-development/27)
- [Ansible User guide](https://docs.ansible.com/ansible/devel/user_guide/index.html)
- [Ansible Developer guide](https://docs.ansible.com/ansible/devel/dev_guide/index.html)
- [Ansible Collections Checklist](https://docs.ansible.com/ansible/devel/community/collection_contributors/collection_requirements.html)
- [Ansible Community code of conduct](https://docs.ansible.com/ansible/devel/community/code_of_conduct.html)
- [The Bullhorn (the Ansible Contributor newsletter)](https://docs.ansible.com/ansible/devel/community/communication.html#the-bullhorn)
- [News for Maintainers](https://forum.ansible.com/tag/news-for-maintainers)

## Licensing

GNU General Public License v3.0 or later.

See [LICENSE](https://www.gnu.org/licenses/gpl-3.0.txt) to see the full text.
