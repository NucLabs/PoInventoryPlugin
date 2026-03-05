# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Your Name <example@domain.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Dynamic inventory plugin that queries a Microsoft SQL Server database.

This plugin retrieves host information from a MSSQL database query. The query must
return at least 'ComputerName' and 'DomainName' fields, which are combined to form the FQDN.
All other fields returned by the query become host variables.

This plugin supports Kerberos authentication for environments that require it.
"""

from __future__ import annotations

DOCUMENTATION = r"""
---
name: mssql
plugin_type: inventory
short_description: Dynamic inventory from Microsoft SQL Server database
description:
  - Retrieves inventory hosts from a Microsoft SQL Server database.
  - Combines C(ComputerName) and C(DomainName) fields from query results to create host FQDNs.
  - All other fields from the query become host variables.
  - Supports Kerberos authentication for Active Directory integrated environments.
author:
  - Your Name (@yourhandle)
version_added: "1.0.0"
requirements:
  - pymssql (Python library)
  - For Kerberos authentication, FreeTDS must be compiled with Kerberos support
  - For Kerberos authentication, a valid Kerberos ticket must be obtained before running (e.g., via kinit)
extends_documentation_fragment:
  - constructed
  - inventory_cache
options:
  plugin:
    description:
      - The name of this plugin.
      - Must be C(ib_pf_ms_bhr.inv_plugins.mssql).
    required: true
    choices: ['ib_pf_ms_bhr.inv_plugins.mssql']
    type: str
  host:
    description:
      - The MSSQL server hostname or IP address.
      - For Kerberos authentication, this should be the fully qualified domain name (FQDN) of the SQL Server.
    required: true
    type: str
    env:
      - name: MSSQL_HOST
  port:
    description:
      - The MSSQL server port.
    required: false
    type: int
    default: 1433
    env:
      - name: MSSQL_PORT
  database:
    description:
      - The database name to connect to.
    required: true
    type: str
    env:
      - name: MSSQL_DATABASE
  auth_method:
    description:
      - The authentication method to use.
      - V(sql) uses SQL Server authentication with username and password.
      - V(kerberos) uses Kerberos/Active Directory integrated authentication.
      - When using V(kerberos), ensure you have a valid Kerberos ticket (run C(kinit) before execution).
    required: false
    type: str
    default: kerberos
    choices: ['sql', 'kerberos']
    env:
      - name: MSSQL_AUTH_METHOD
  username:
    description:
      - The username for database authentication.
      - Required when O(auth_method=sql).
      - Ignored when O(auth_method=kerberos).
    required: false
    type: str
    env:
      - name: MSSQL_USERNAME
  password:
    description:
      - The password for database authentication.
      - Required when O(auth_method=sql).
      - Ignored when O(auth_method=kerberos).
    required: false
    type: str
    env:
      - name: MSSQL_PASSWORD
    no_log: true
  query:
    description:
      - The SQL query to execute.
      - Must return at least C(ComputerName) and C(DomainName) columns.
      - All other columns become host variables.
    required: true
    type: str
  connect_timeout:
    description:
      - Connection timeout in seconds.
    required: false
    type: int
    default: 30
  query_timeout:
    description:
      - Query execution timeout in seconds.
    required: false
    type: int
    default: 60
  tds_version:
    description:
      - The TDS protocol version to use.
      - Generally V(7.3) or higher is recommended for modern SQL Server versions.
      - May need to be adjusted based on SQL Server version.
    required: false
    type: str
    default: "7.3"
    choices: ['7.0', '7.1', '7.2', '7.3', '7.4']
  groups:
    description:
      - Add hosts to groups based on Jinja2 conditionals.
    required: false
    type: dict
    default: {}
  keyed_groups:
    description:
      - Add hosts to groups based on the values of a variable.
    required: false
    type: list
    elements: dict
    default: []
  compose:
    description:
      - Create variables based on Jinja2 expressions.
    required: false
    type: dict
    default: {}
  strict:
    description:
      - If V(true), fail if any templating errors occur.
    required: false
    type: bool
    default: false
  leading_separator:
    description:
      - Use a leading separator for keyed groups.
    required: false
    type: bool
    default: true
  var_prefix:
    description:
      - Prefix to add to all host variables from the query results.
      - Set to an empty string C('') for no prefix.
      - Useful for namespacing variables to avoid collisions with other inventory sources.
    required: false
    type: str
    default: ''
    env:
      - name: MSSQL_VAR_PREFIX
notes:
  - The query must return C(ComputerName) and C(DomainName) columns.
  - The FQDN is constructed as C(ComputerName.DomainName).
  - Column names are converted to lowercase for consistency.
  - NULL values in the database are converted to None in Python.
  - "Kerberos authentication requires:"
  - "  1. FreeTDS compiled with Kerberos support (libgssapi)"
  - "  2. Proper krb5.conf configuration pointing to your Active Directory domain"
  - "  3. A valid Kerberos ticket obtained via C(kinit username@REALM) before running"
  - "  4. The SQL Server host should be specified as FQDN for SPN resolution"
  - For automated/unattended Kerberos authentication, consider using a keytab file with C(kinit -k -t /path/to/keytab principal@REALM).
seealso:
  - module: community.general.mssql_db
"""

EXAMPLES = r"""
# Kerberos authentication (default) - mssql_inventory.mssql.yml
# Ensure you have a valid Kerberos ticket: kinit username@DOMAIN.COM
---
plugin: ib_pf_ms_bhr.inv_plugins.mssql
host: sqlserver.domain.com
database: inventory_db
query: |
  SELECT ComputerName, DomainName, os_type, environment, location
  FROM servers
  WHERE active = 1

# Kerberos with all options
---
plugin: ib_pf_ms_bhr.inv_plugins.mssql
host: sqlserver.domain.com
port: 1433
database: cmdb
auth_method: kerberos
tds_version: "7.3"
query: |
  SELECT
    s.name,
    s.domainname,
    s.os_type,
    s.environment,
    s.datacenter,
    s.cpu_count,
    s.memory_gb
  FROM servers s
  WHERE s.status = 'active'
connect_timeout: 30
query_timeout: 120
strict: false
compose:
  ansible_host: inventory_hostname
  total_memory_mb: memory_gb * 1024
keyed_groups:
  - prefix: env
    key: environment
  - prefix: os
    key: os_type
  - prefix: dc
    key: datacenter
groups:
  linux: os_type == 'Linux'
  windows: os_type == 'Windows'
  production: environment == 'prod'

# SQL Server authentication (username/password)
---
plugin: ib_pf_ms_bhr.inv_plugins.mssql
host: sqlserver.example.com
database: inventory_db
auth_method: sql
username: ansible_user
password: "{{ lookup('env', 'MSSQL_PASSWORD') }}"
query: |
  SELECT ComputerName, DomainName, os_type, environment, location
  FROM servers
  WHERE active = 1

# SQL auth with vault-encrypted password
---
plugin: ib_pf_ms_bhr.inv_plugins.mssql
host: sqlserver.example.com
port: 1433
database: cmdb
auth_method: sql
username: ansible_reader
password: !vault |
  $ANSIBLE_VAULT;1.1;AES256
  ...
query: |
  SELECT
    s.ComputerName,
    s.DomainName,
    s.os_type,
    s.environment,
    s.datacenter,
    s.cpu_count,
    s.memory_gb
  FROM servers s
  WHERE s.status = 'active'
connect_timeout: 30
query_timeout: 120
strict: false
compose:
  ansible_host: inventory_hostname
  total_memory_mb: memory_gb * 1024
keyed_groups:
  - prefix: env
    key: environment
  - prefix: os
    key: os_type
  - prefix: dc
    key: datacenter
groups:
  linux: os_type == 'Linux'
  windows: os_type == 'Windows'
  production: environment == 'prod'
"""

from typing import TYPE_CHECKING, Any  # noqa: E402

from ansible.errors import AnsibleError, AnsibleParserError  # noqa: E402
from ansible.plugins.inventory import (  # noqa: E402
    BaseInventoryPlugin,
    Cacheable,
    Constructable,
)

if TYPE_CHECKING:
    from ansible.inventory.data import InventoryData
    from ansible.parsing.dataloader import DataLoader


class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):
    """Dynamic inventory plugin for Microsoft SQL Server databases.

    This plugin queries a MSSQL database and creates inventory hosts from the results.
    The 'ComputerName' and 'DomainName' fields are combined to create the FQDN, and all other
    fields become host variables.
    """

    NAME = "ib_pf_ms_bhr.inv_plugins.mssql"

    def __init__(self) -> None:
        """Initialize the inventory plugin."""
        super().__init__()
        self._connection: Any = None

    def verify_file(self, path: str) -> bool:
        """Verify that the inventory source file is valid.

        Args:
            path: Path to the inventory source file.

        Returns:
            True if the file is valid for this plugin.
        """
        valid = False
        if super().verify_file(path):
            if path.endswith((".mssql.yml", ".mssql.yaml")):
                valid = True
        return valid

    def _get_connection(self) -> Any:
        """Establish a connection to the MSSQL database.

        Supports both Kerberos and SQL Server authentication methods.
        For Kerberos, a valid ticket must be obtained before running (via kinit).

        Returns:
            A pymssql connection object.

        Raises:
            AnsibleError: If connection fails or pymssql is not installed.
        """
        try:
            import pymssql  # pylint: disable=import-outside-toplevel
        except ImportError as err:
            msg = (
                "The pymssql library is required for the mssql inventory plugin. "
                "Install it with: pip install pymssql"
            )
            raise AnsibleError(msg) from err

        host = self.get_option("host")
        port = self.get_option("port")
        database = self.get_option("database")
        auth_method = self.get_option("auth_method")
        connect_timeout = self.get_option("connect_timeout")
        tds_version = self.get_option("tds_version")

        # Build connection parameters based on authentication method
        connect_params: dict[str, Any] = {
            "server": host,
            "port": port,
            "database": database,
            "login_timeout": connect_timeout,
            "as_dict": True,
            "tds_version": tds_version,
        }

        if auth_method == "kerberos":
            # Kerberos authentication - do not pass user/password
            # pymssql/FreeTDS will use the current Kerberos ticket
            self.display.vvv(f"Using Kerberos authentication to connect to {host}")

            # Verify Kerberos ticket exists
            self._check_kerberos_ticket()
        else:
            # SQL Server authentication
            username = self.get_option("username")
            password = self.get_option("password")

            if not username or not password:
                msg = (
                    "Username and password are required when using SQL Server "
                    "authentication (auth_method=sql)"
                )
                raise AnsibleError(msg)

            connect_params["user"] = username
            connect_params["password"] = password
            self.display.vvv(
                f"Using SQL authentication to connect to {host} as {username}"
            )

        try:
            connection = pymssql.connect(**connect_params)
        except pymssql.Error as err:
            error_msg = str(err)
            if auth_method == "kerberos" and (
                "login" in error_msg.lower() or "auth" in error_msg.lower()
            ):
                msg = (
                    f"Failed to connect to MSSQL server {host}:{port} with Kerberos: {err}. "
                    "Ensure you have a valid Kerberos ticket (run 'klist' to check, "
                    "'kinit username@REALM' to obtain one) and that the server FQDN is correct."
                )
            else:
                msg = f"Failed to connect to MSSQL server {host}:{port}: {err}"
            raise AnsibleError(msg) from err

        return connection

    def _check_kerberos_ticket(self) -> None:
        """Check if a valid Kerberos ticket exists.

        Raises:
            AnsibleError: If no valid Kerberos ticket is found.
        """
        import shutil  # pylint: disable=import-outside-toplevel
        import subprocess  # pylint: disable=import-outside-toplevel

        klist_path = shutil.which("klist")
        if not klist_path:
            self.display.warning(
                "Cannot verify Kerberos ticket: 'klist' command not found. "
                "Proceeding anyway, but connection may fail if no valid ticket exists."
            )
            return

        try:
            result = subprocess.run(
                [klist_path, "-s"],
                capture_output=True,
                timeout=10,
                check=False,
            )
            if result.returncode != 0:
                msg = (
                    "No valid Kerberos ticket found. Please obtain a ticket using "
                    "'kinit username@REALM' before running this inventory plugin. "
                    "For automated environments, consider using a keytab file: "
                    "'kinit -k -t /path/to/keytab principal@REALM'"
                )
                raise AnsibleError(msg)
            self.display.vvv("Valid Kerberos ticket found")
        except subprocess.TimeoutExpired:
            self.display.warning("Timeout checking Kerberos ticket, proceeding anyway")
        except FileNotFoundError:
            self.display.warning("Could not run klist, proceeding anyway")

    def _execute_query(self) -> list[dict[str, Any]]:
        """Execute the SQL query and return results.

        Returns:
            A list of dictionaries representing query results.

        Raises:
            AnsibleError: If query execution fails.
        """
        try:
            import pymssql  # pylint: disable=import-outside-toplevel
        except ImportError as err:
            msg = "The pymssql library is required."
            raise AnsibleError(msg) from err

        query = self.get_option("query")
        query_timeout = self.get_option("query_timeout")

        connection = self._get_connection()
        try:
            cursor = connection.cursor()
            cursor.execute(query)
            # Set query timeout if the driver supports it
            if hasattr(cursor, "set_timeout"):
                cursor.set_timeout(query_timeout)

            results: list[dict[str, Any]] = []
            for row in cursor:
                # Convert column names to lowercase for consistency
                normalized_row = {k.lower(): v for k, v in row.items()}
                results.append(normalized_row)

            return results
        except pymssql.Error as err:
            msg = f"Failed to execute query: {err}"
            raise AnsibleError(msg) from err
        finally:
            connection.close()

    def _validate_row(self, row: dict[str, Any], row_index: int) -> bool:
        """Validate that a row contains required fields.

        Args:
            row: Dictionary representing a database row.
            row_index: Index of the row for error reporting.

        Returns:
            True if the row is valid.

        Raises:
            AnsibleParserError: If required fields are missing.
        """
        required_fields = ("computername", "domainname")
        missing_fields = [field for field in required_fields if field not in row]

        if missing_fields:
            msg = (
                f"Row {row_index} is missing required fields: {', '.join(missing_fields)}. "
                f"Available fields: {', '.join(row.keys())}"
            )
            raise AnsibleParserError(msg)

        if not row["computername"] or not row["domainname"]:
            self.display.warning(
                f"Row {row_index} has empty 'computername' or 'domainname' field, skipping."
            )
            return False

        return True

    def _build_fqdn(self, computername: str, domainname: str) -> str:
        """Build FQDN from computer name and domain name.

        Args:
            computername: The hostname part.
            domainname: The domain name part.

        Returns:
            The fully qualified domain name.
        """
        # Strip whitespace and ensure clean concatenation
        computername = str(computername).strip()
        domainname = str(domainname).strip()

        # Handle cases where domainname might already start with a dot
        if domainname.startswith("."):
            return f"{computername}{domainname}"
        return f"{computername}.{domainname}"

    def _populate_inventory(self, results: list[dict[str, Any]]) -> None:
        """Populate the inventory with hosts from query results.

        Args:
            results: List of dictionaries from the database query.
        """
        strict = self.get_option("strict")
        var_prefix = self.get_option("var_prefix") or ""

        for idx, row in enumerate(results):
            if not self._validate_row(row, idx):
                continue

            # Build the FQDN from computername and domainname
            fqdn = self._build_fqdn(row["computername"], row["domainname"])

            # Add host to inventory
            self.inventory.add_host(fqdn)

            # Add all fields as host variables with optional prefix
            for key, value in row.items():
                # Strip whitespace from string values (common with SQL CHAR columns)
                if isinstance(value, str):
                    value = value.strip()
                prefixed_key = f"{var_prefix}{key}"
                self.inventory.set_variable(fqdn, prefixed_key, value)

            # Apply constructed features (groups, keyed_groups, compose)
            # Get all variables for this host for constructed features
            # Note: hostvars for constructed features use unprefixed keys for easier access
            hostvars = {}
            for key, value in row.items():
                # Strip whitespace from string values
                if isinstance(value, str):
                    value = value.strip()
                hostvars[key] = value
            hostvars["inventory_hostname"] = fqdn

            # Set composed variables
            self._set_composite_vars(
                self.get_option("compose"),
                hostvars,
                fqdn,
                strict=strict,
            )

            # Add host to groups based on conditionals
            self._add_host_to_composed_groups(
                self.get_option("groups"),
                hostvars,
                fqdn,
                strict=strict,
            )

            # Add host to keyed groups
            self._add_host_to_keyed_groups(
                self.get_option("keyed_groups"),
                hostvars,
                fqdn,
                strict=strict,
            )

    def parse(
        self,
        inventory: "InventoryData",
        loader: "DataLoader",
        path: str,
        cache: bool = True,
    ) -> None:
        """Parse the inventory source and populate inventory.

        Args:
            inventory: The inventory data object to populate.
            loader: The data loader.
            path: Path to the inventory source file.
            cache: Whether to use caching.
        """
        super().parse(inventory, loader, path, cache)

        self._read_config_data(path)

        cache_key = self.get_cache_key(path)
        use_cache = self.get_option("cache") and cache
        update_cache = False

        results: list[dict[str, Any]] = []

        if use_cache:
            try:
                results = self._cache[cache_key]
            except KeyError:
                update_cache = True

        if not use_cache or update_cache:
            results = self._execute_query()

        if update_cache:
            self._cache[cache_key] = results

        self._populate_inventory(results)
