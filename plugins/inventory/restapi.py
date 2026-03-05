# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Your Name <example@domain.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Dynamic inventory plugin that queries a REST API.

This plugin retrieves host information from a REST API endpoint. The API must
return a JSON array of objects containing at least 'ComputerName' and 'DomainName' fields,
which are combined to form the FQDN. All other fields become host variables.

This plugin supports both open (no authentication) and bearer token authentication.
"""

from __future__ import annotations

DOCUMENTATION = r"""
---
name: restapi
plugin_type: inventory
short_description: Dynamic inventory from REST API
description:
  - Retrieves inventory hosts from a REST API endpoint.
  - Combines C(ComputerName) and C(DomainName) fields from the response to create host FQDNs.
  - All other fields from the response become host variables.
  - Supports both open (no authentication) and bearer token authentication.
author:
  - Your Name (@yourhandle)
version_added: "1.0.0"
requirements:
  - requests (Python library)
extends_documentation_fragment:
  - constructed
  - inventory_cache
options:
  plugin:
    description:
      - The name of this plugin.
      - Must be C(ib_pf_ms_bhr.inv_plugins.restapi).
    required: true
    choices: ['ib_pf_ms_bhr.inv_plugins.restapi']
    type: str
  url:
    description:
      - The REST API endpoint URL.
      - Must return a JSON array of objects containing at least C(ComputerName) and C(DomainName) fields.
    required: true
    type: str
    env:
      - name: RESTAPI_URL
  auth_method:
    description:
      - The authentication method to use.
      - V(none) uses no authentication (open API).
      - V(bearer) uses bearer token authentication.
    required: false
    type: str
    default: none
    choices: ['none', 'bearer']
    env:
      - name: RESTAPI_AUTH_METHOD
  bearer_token:
    description:
      - The bearer token for authentication.
      - Required when O(auth_method=bearer).
      - Ignored when O(auth_method=none).
    required: false
    type: str
    env:
      - name: RESTAPI_BEARER_TOKEN
    no_log: true
  timeout:
    description:
      - The request timeout in seconds.
    required: false
    type: int
    default: 30
    env:
      - name: RESTAPI_TIMEOUT
  validate_certs:
    description:
      - Whether to validate SSL/TLS certificates.
      - Set to V(false) for self-signed certificates (not recommended for production).
    required: false
    type: bool
    default: true
    env:
      - name: RESTAPI_VALIDATE_CERTS
  ca_cert:
    description:
      - Path to a CA certificate bundle to use for SSL/TLS verification.
      - If not specified, the system default CA bundle is used.
    required: false
    type: path
    env:
      - name: RESTAPI_CA_CERT
  headers:
    description:
      - Additional HTTP headers to send with the request.
      - Specified as a dictionary of header name/value pairs.
    required: false
    type: dict
    default: {}
  strict:
    description:
      - If V(true), make invalid entries a fatal error.
      - If V(false), skip invalid entries and continue.
    type: bool
    default: false
  var_prefix:
    description:
      - Prefix to add to all host variables from the API response.
      - Set to an empty string C('') for no prefix.
      - Useful for namespacing variables to avoid collisions with other inventory sources.
    required: false
    type: str
    default: ''
    env:
      - name: RESTAPI_VAR_PREFIX
notes:
  - The REST API must return a JSON array of objects.
  - Each object must contain at least C(ComputerName) and C(DomainName) fields.
  - Field names are normalized to lowercase for consistency.
  - String values are automatically trimmed of leading/trailing whitespace.
seealso:
  - module: ansible.builtin.uri
"""

EXAMPLES = r"""
# Minimal configuration - open API with no authentication
---
plugin: ib_pf_ms_bhr.inv_plugins.restapi
url: http://api.example.com/servers

# Bearer token authentication
---
plugin: ib_pf_ms_bhr.inv_plugins.restapi
url: https://api.example.com/servers
auth_method: bearer
bearer_token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# With custom headers
---
plugin: ib_pf_ms_bhr.inv_plugins.restapi
url: https://api.example.com/servers
headers:
  X-Custom-Header: "custom-value"
  Accept: "application/json"

# With SSL certificate verification disabled (for testing only)
---
plugin: ib_pf_ms_bhr.inv_plugins.restapi
url: https://self-signed.example.com/servers
validate_certs: false

# With custom CA certificate
---
plugin: ib_pf_ms_bhr.inv_plugins.restapi
url: https://internal.example.com/servers
ca_cert: /path/to/ca-bundle.crt

# Using environment variables for sensitive data
---
plugin: ib_pf_ms_bhr.inv_plugins.restapi
url: "{{ lookup('env', 'RESTAPI_URL') }}"
auth_method: bearer
bearer_token: "{{ lookup('env', 'RESTAPI_BEARER_TOKEN') }}"

# Using caching to reduce API calls
---
plugin: ib_pf_ms_bhr.inv_plugins.restapi
url: https://api.example.com/servers
cache: true
cache_plugin: ansible.builtin.jsonfile
cache_timeout: 3600
cache_connection: /tmp/restapi_inventory_cache

# Using constructed features to create groups
---
plugin: ib_pf_ms_bhr.inv_plugins.restapi
url: https://api.example.com/servers
keyed_groups:
  - key: environment
    prefix: env
  - key: datacenter
    separator: ""
groups:
  production: environment == 'prod'
  webservers: "'web' in role"
compose:
  ansible_host: ip_address
  custom_var: "'prefix_' + name"
"""

from typing import TYPE_CHECKING, Any

from ansible.errors import AnsibleError, AnsibleParserError
from ansible.plugins.inventory import BaseInventoryPlugin, Cacheable, Constructable

if TYPE_CHECKING:
    from ansible.inventory.data import InventoryData
    from ansible.parsing.dataloader import DataLoader


class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):
    """Dynamic inventory plugin that retrieves hosts from a REST API.

    This plugin queries a REST API endpoint and uses the returned data to populate
    the Ansible inventory. The API must return a JSON array of objects containing
    at least 'name' and 'domainname' fields.
    """

    NAME = "ib_pf_ms_bhr.inv_plugins.restapi"

    def verify_file(self, path: str) -> bool:
        """Verify that the inventory source file is valid.

        This method checks if the file has an appropriate extension for this plugin.

        Args:
            path: Path to the inventory source file.

        Returns:
            True if the file appears to be valid for this plugin, False otherwise.
        """
        valid = False
        if super().verify_file(path):
            # Accept files ending with specific extensions
            valid_extensions = (
                "restapi.yml",
                "restapi.yaml",
                "restapi.json",
            )
            if path.endswith(valid_extensions):
                valid = True
        return valid

    def _validate_options(self) -> None:
        """Validate plugin configuration options.

        Raises:
            AnsibleParserError: If required options are missing or invalid.
        """
        url = self.get_option("url")
        if not url:
            msg = "The 'url' option is required."
            raise AnsibleParserError(msg)

        auth_method = self.get_option("auth_method")
        if auth_method == "bearer":
            bearer_token = self.get_option("bearer_token")
            if not bearer_token:
                msg = "The 'bearer_token' option is required when auth_method is 'bearer'."
                raise AnsibleParserError(msg)

    def _build_headers(self) -> dict[str, str]:
        """Build HTTP headers for the API request.

        Returns:
            Dictionary of HTTP headers.
        """
        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        # Add custom headers from configuration
        custom_headers = self.get_option("headers") or {}
        headers.update(custom_headers)

        # Add authorization header if using bearer token
        auth_method = self.get_option("auth_method")
        if auth_method == "bearer":
            self.display.vvv("Using bearer token authentication")
            bearer_token = self.get_option("bearer_token")
            headers["Authorization"] = f"Bearer {bearer_token}"
        else:
            self.display.vvv("Using no authentication")

        return headers

    def _make_request(self) -> list[dict[str, Any]]:
        """Make the HTTP request to the REST API.

        Returns:
            A list of dictionaries representing the API response.

        Raises:
            AnsibleError: If the request fails or returns invalid data.
        """
        try:
            import requests  # pylint: disable=import-outside-toplevel
        except ImportError as err:
            msg = (
                "The 'requests' library is required for the restapi inventory plugin. "
                "Install it with: pip install requests"
            )
            raise AnsibleError(msg) from err

        url = self.get_option("url")
        timeout = self.get_option("timeout")
        validate_certs = self.get_option("validate_certs")
        ca_cert = self.get_option("ca_cert")

        headers = self._build_headers()

        # Configure SSL verification
        verify: bool | str = validate_certs
        if validate_certs and ca_cert:
            verify = ca_cert

        try:
            self.display.vvv(f"Making request to {url}")
            response = requests.get(
                url,
                headers=headers,
                timeout=timeout,
                verify=verify,
            )
            response.raise_for_status()
        except requests.exceptions.SSLError as err:
            msg = (
                f"SSL certificate verification failed for {url}: {err}. "
                "Consider using 'validate_certs: false' for testing or "
                "provide a valid CA certificate with 'ca_cert'."
            )
            raise AnsibleError(msg) from err
        except requests.exceptions.Timeout as err:
            msg = f"Request to {url} timed out after {timeout} seconds."
            raise AnsibleError(msg) from err
        except requests.exceptions.ConnectionError as err:
            msg = f"Failed to connect to {url}: {err}"
            raise AnsibleError(msg) from err
        except requests.exceptions.HTTPError as err:
            msg = f"HTTP error from {url}: {response.status_code} - {response.text}"
            raise AnsibleError(msg) from err
        except requests.exceptions.RequestException as err:
            msg = f"Request to {url} failed: {err}"
            raise AnsibleError(msg) from err

        # Parse JSON response
        try:
            data = response.json()
        except ValueError as err:
            msg = f"Invalid JSON response from {url}: {err}"
            raise AnsibleError(msg) from err

        # Validate response format
        if not isinstance(data, list):
            msg = (
                f"Expected a JSON array from {url}, but got {type(data).__name__}. "
                "The API must return a JSON array of objects."
            )
            raise AnsibleError(msg)

        # Normalize field names to lowercase
        results: list[dict[str, Any]] = []
        for item in data:
            if not isinstance(item, dict):
                self.display.warning(
                    f"Skipping non-object item in API response: {item}"
                )
                continue
            normalized_item = {k.lower(): v for k, v in item.items()}
            results.append(normalized_item)

        return results

    def _validate_row(self, row: dict[str, Any], row_index: int) -> bool:
        """Validate that a row contains required fields.

        Args:
            row: Dictionary representing an API response item.
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
                f"Item {row_index} is missing required fields: {', '.join(missing_fields)}. "
                f"Available fields: {', '.join(row.keys())}"
            )
            raise AnsibleParserError(msg)

        if not row["computername"] or not row["domainname"]:
            self.display.warning(
                f"Item {row_index} has empty 'computername' or 'domainname' field, skipping."
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
        """Populate the inventory with hosts from API response.

        Args:
            results: List of dictionaries from the API response.
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
                # Strip whitespace from string values
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
        self._validate_options()

        # Handle caching
        cache_key = self.get_cache_key(path)
        user_cache_setting = self.get_option("cache")
        attempt_to_read_cache = user_cache_setting and cache
        cache_needs_update = user_cache_setting and not cache

        results = None

        if attempt_to_read_cache:
            try:
                results = self._cache[cache_key]
                self.display.vvv(f"Using cached data for {path}")
            except KeyError:
                cache_needs_update = True

        if results is None:
            results = self._make_request()

        if cache_needs_update:
            self._cache[cache_key] = results
            self.display.vvv(f"Cached data for {path}")

        self._populate_inventory(results)
