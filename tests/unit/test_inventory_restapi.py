# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Your Name <example@domain.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Unit tests for the REST API dynamic inventory plugin."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, Mock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

# Add the project root to the path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import the actual plugin module
from plugins.inventory.restapi import InventoryModule


@pytest.fixture
def inventory_plugin() -> Generator[InventoryModule, None, None]:
    """Create an instance of the REST API inventory plugin for testing."""
    plugin = InventoryModule()
    plugin.inventory = MagicMock()
    plugin.display = MagicMock()
    plugin._options: dict[str, Any] = {}

    # Override get_option to use our _options dict
    plugin.get_option = lambda x: plugin._options.get(x)  # type: ignore[method-assign]

    yield plugin


class TestInventoryModuleVerifyFile:
    """Tests for the verify_file method."""

    def test_verify_file_valid_restapi_yml(self) -> None:
        """Test that .restapi.yml files are accepted."""
        path = "/path/to/inventory.restapi.yml"
        valid = path.endswith((".restapi.yml", ".restapi.yaml", ".restapi.json"))
        assert valid is True

    def test_verify_file_valid_restapi_yaml(self) -> None:
        """Test that .restapi.yaml files are accepted."""
        path = "/path/to/inventory.restapi.yaml"
        valid = path.endswith((".restapi.yml", ".restapi.yaml", ".restapi.json"))
        assert valid is True

    def test_verify_file_valid_restapi_json(self) -> None:
        """Test that .restapi.json files are accepted."""
        path = "/path/to/inventory.restapi.json"
        valid = path.endswith((".restapi.yml", ".restapi.yaml", ".restapi.json"))
        assert valid is True

    def test_verify_file_invalid_extension(self) -> None:
        """Test that non-restapi files are rejected."""
        path = "/path/to/inventory.yml"
        valid = path.endswith((".restapi.yml", ".restapi.yaml", ".restapi.json"))
        assert valid is False


class TestValidateOptions:
    """Tests for the _validate_options method."""

    def test_validate_options_valid_no_auth(
        self, inventory_plugin: InventoryModule
    ) -> None:
        """Test validation passes with no auth."""
        inventory_plugin._options = {
            "url": "http://api.example.com/servers",
            "auth_method": "none",
        }
        # Should not raise
        inventory_plugin._validate_options()

    def test_validate_options_valid_bearer(
        self, inventory_plugin: InventoryModule
    ) -> None:
        """Test validation passes with bearer auth."""
        inventory_plugin._options = {
            "url": "http://api.example.com/servers",
            "auth_method": "bearer",
            "bearer_token": "test-token",
        }
        # Should not raise
        inventory_plugin._validate_options()

    def test_validate_options_missing_url(
        self, inventory_plugin: InventoryModule
    ) -> None:
        """Test validation fails with missing URL."""
        from ansible.errors import AnsibleParserError

        inventory_plugin._options = {
            "url": None,
            "auth_method": "none",
        }
        with pytest.raises(AnsibleParserError, match="'url' option is required"):
            inventory_plugin._validate_options()

    def test_validate_options_bearer_missing_token(
        self, inventory_plugin: InventoryModule
    ) -> None:
        """Test validation fails with bearer auth but no token."""
        from ansible.errors import AnsibleParserError

        inventory_plugin._options = {
            "url": "http://api.example.com/servers",
            "auth_method": "bearer",
            "bearer_token": None,
        }
        with pytest.raises(
            AnsibleParserError, match="'bearer_token' option is required"
        ):
            inventory_plugin._validate_options()


class TestBuildHeaders:
    """Tests for the _build_headers method."""

    def test_build_headers_no_auth(self, inventory_plugin: InventoryModule) -> None:
        """Test header building with no auth."""
        inventory_plugin._options = {
            "auth_method": "none",
            "headers": {},
        }
        headers = inventory_plugin._build_headers()
        assert headers["Accept"] == "application/json"
        assert headers["Content-Type"] == "application/json"
        assert "Authorization" not in headers

    def test_build_headers_bearer_auth(
        self, inventory_plugin: InventoryModule
    ) -> None:
        """Test header building with bearer auth."""
        inventory_plugin._options = {
            "auth_method": "bearer",
            "bearer_token": "test-token-123",
            "headers": {},
        }
        headers = inventory_plugin._build_headers()
        assert headers["Authorization"] == "Bearer test-token-123"

    def test_build_headers_custom_headers(
        self, inventory_plugin: InventoryModule
    ) -> None:
        """Test header building with custom headers."""
        inventory_plugin._options = {
            "auth_method": "none",
            "headers": {
                "X-Custom-Header": "custom-value",
                "X-Another": "another-value",
            },
        }
        headers = inventory_plugin._build_headers()
        assert headers["X-Custom-Header"] == "custom-value"
        assert headers["X-Another"] == "another-value"

    def test_build_headers_custom_overrides_default(
        self, inventory_plugin: InventoryModule
    ) -> None:
        """Test that custom headers can override defaults."""
        inventory_plugin._options = {
            "auth_method": "none",
            "headers": {
                "Accept": "text/plain",
            },
        }
        headers = inventory_plugin._build_headers()
        assert headers["Accept"] == "text/plain"


class TestBuildFqdn:
    """Tests for the _build_fqdn method."""

    def test_build_fqdn_simple(self, inventory_plugin: InventoryModule) -> None:
        """Test basic FQDN construction."""
        result = inventory_plugin._build_fqdn("server01", "example.com")
        assert result == "server01.example.com"

    def test_build_fqdn_with_whitespace(
        self, inventory_plugin: InventoryModule
    ) -> None:
        """Test FQDN construction with whitespace."""
        result = inventory_plugin._build_fqdn("  server01  ", "  example.com  ")
        assert result == "server01.example.com"

    def test_build_fqdn_domain_with_leading_dot(
        self, inventory_plugin: InventoryModule
    ) -> None:
        """Test FQDN construction when domain starts with dot."""
        result = inventory_plugin._build_fqdn("server01", ".example.com")
        assert result == "server01.example.com"

    def test_build_fqdn_subdomain(self, inventory_plugin: InventoryModule) -> None:
        """Test FQDN construction with subdomain."""
        result = inventory_plugin._build_fqdn("server01", "prod.example.com")
        assert result == "server01.prod.example.com"


class TestValidateRow:
    """Tests for the _validate_row method."""

    def test_validate_row_valid(self, inventory_plugin: InventoryModule) -> None:
        """Test validation of a valid row."""
        row: dict[str, Any] = {
            "computername": "server01",
            "domainname": "example.com",
            "os": "linux",
        }
        result = inventory_plugin._validate_row(row, 0)
        assert result is True

    def test_validate_row_empty_computername(self, inventory_plugin: InventoryModule) -> None:
        """Test validation fails with empty computername."""
        row: dict[str, Any] = {"computername": "", "domainname": "example.com"}
        result = inventory_plugin._validate_row(row, 0)
        assert result is False
        inventory_plugin.display.warning.assert_called()  # type: ignore[union-attr]

    def test_validate_row_empty_domainname(
        self, inventory_plugin: InventoryModule
    ) -> None:
        """Test validation fails with empty domainname."""
        row: dict[str, Any] = {"computername": "server01", "domainname": ""}
        result = inventory_plugin._validate_row(row, 0)
        assert result is False

    def test_validate_row_none_values(
        self, inventory_plugin: InventoryModule
    ) -> None:
        """Test validation fails with None values."""
        row: dict[str, Any] = {"computername": None, "domainname": "example.com"}
        result = inventory_plugin._validate_row(row, 0)
        assert result is False


class TestMakeRequest:
    """Tests for the _make_request method."""

    def test_make_request_success(
        self, inventory_plugin: InventoryModule
    ) -> None:
        """Test successful API request."""
        inventory_plugin._options = {
            "url": "http://api.example.com/servers",
            "timeout": 30,
            "validate_certs": True,
            "ca_cert": None,
            "auth_method": "none",
            "headers": {},
        }

        mock_response = Mock()
        mock_response.json.return_value = [
            {"computername": "server01", "domainname": "example.com"},
        ]
        mock_response.raise_for_status = Mock()

        with patch.dict("sys.modules", {"requests": MagicMock()}):
            import sys

            mock_requests = sys.modules["requests"]
            mock_requests.get.return_value = mock_response

            # Need to reload the module to pick up the mocked requests
            with patch("requests.get", return_value=mock_response) as mock_get:
                with patch("requests.exceptions") as mock_exceptions:
                    # Import requests for the test
                    import requests

                    results = inventory_plugin._make_request()

        assert len(results) == 1
        assert results[0]["computername"] == "server01"

    def test_make_request_normalizes_keys(
        self, inventory_plugin: InventoryModule
    ) -> None:
        """Test that field names are normalized to lowercase."""
        inventory_plugin._options = {
            "url": "http://api.example.com/servers",
            "timeout": 30,
            "validate_certs": True,
            "ca_cert": None,
            "auth_method": "none",
            "headers": {},
        }

        mock_response = Mock()
        mock_response.json.return_value = [
            {"ComputerName": "server01", "DomainName": "example.com", "OS_TYPE": "linux"},
        ]
        mock_response.raise_for_status = Mock()

        with patch("requests.get", return_value=mock_response):
            results = inventory_plugin._make_request()

        assert "computername" in results[0]
        assert "domainname" in results[0]
        assert "os_type" in results[0]

    def test_make_request_connection_error(
        self, inventory_plugin: InventoryModule
    ) -> None:
        """Test handling of connection errors."""
        from ansible.errors import AnsibleError

        inventory_plugin._options = {
            "url": "http://api.example.com/servers",
            "timeout": 30,
            "validate_certs": True,
            "ca_cert": None,
            "auth_method": "none",
            "headers": {},
        }

        import requests

        with patch(
            "requests.get",
            side_effect=requests.exceptions.ConnectionError("Connection refused"),
        ):
            with pytest.raises(AnsibleError, match="Failed to connect"):
                inventory_plugin._make_request()

    def test_make_request_timeout(
        self, inventory_plugin: InventoryModule
    ) -> None:
        """Test handling of timeout errors."""
        from ansible.errors import AnsibleError

        inventory_plugin._options = {
            "url": "http://api.example.com/servers",
            "timeout": 30,
            "validate_certs": True,
            "ca_cert": None,
            "auth_method": "none",
            "headers": {},
        }

        import requests

        with patch("requests.get", side_effect=requests.exceptions.Timeout("Timeout")):
            with pytest.raises(AnsibleError, match="timed out"):
                inventory_plugin._make_request()

    def test_make_request_invalid_json(
        self, inventory_plugin: InventoryModule
    ) -> None:
        """Test handling of invalid JSON response."""
        from ansible.errors import AnsibleError

        inventory_plugin._options = {
            "url": "http://api.example.com/servers",
            "timeout": 30,
            "validate_certs": True,
            "ca_cert": None,
            "auth_method": "none",
            "headers": {},
        }

        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = Mock()

        with patch("requests.get", return_value=mock_response):
            with pytest.raises(AnsibleError, match="Invalid JSON"):
                inventory_plugin._make_request()

    def test_make_request_not_array(
        self, inventory_plugin: InventoryModule
    ) -> None:
        """Test handling of non-array JSON response."""
        from ansible.errors import AnsibleError

        inventory_plugin._options = {
            "url": "http://api.example.com/servers",
            "timeout": 30,
            "validate_certs": True,
            "ca_cert": None,
            "auth_method": "none",
            "headers": {},
        }

        mock_response = Mock()
        mock_response.json.return_value = {"servers": []}  # Object, not array
        mock_response.raise_for_status = Mock()

        with patch("requests.get", return_value=mock_response):
            with pytest.raises(AnsibleError, match="Expected a JSON array"):
                inventory_plugin._make_request()

    def test_make_request_with_ca_cert(
        self, inventory_plugin: InventoryModule
    ) -> None:
        """Test request with custom CA certificate."""
        inventory_plugin._options = {
            "url": "https://api.example.com/servers",
            "timeout": 30,
            "validate_certs": True,
            "ca_cert": "/path/to/ca-bundle.crt",
            "auth_method": "none",
            "headers": {},
        }

        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = Mock()

        with patch("requests.get", return_value=mock_response) as mock_get:
            inventory_plugin._make_request()

            mock_get.assert_called_once_with(
                "https://api.example.com/servers",
                headers=inventory_plugin._build_headers(),
                timeout=30,
                verify="/path/to/ca-bundle.crt",
            )


class TestPopulateInventory:
    """Tests for the _populate_inventory method."""

    def test_populate_inventory_single_host(
        self, inventory_plugin: InventoryModule
    ) -> None:
        """Test populating inventory with a single host."""
        inventory_plugin._options = {
            "strict": False,
            "compose": {},
            "groups": {},
            "keyed_groups": [],
            "var_prefix": "",
        }
        inventory_plugin._set_composite_vars = MagicMock()  # type: ignore[method-assign]
        inventory_plugin._add_host_to_composed_groups = MagicMock()  # type: ignore[method-assign]
        inventory_plugin._add_host_to_keyed_groups = MagicMock()  # type: ignore[method-assign]

        results: list[dict[str, Any]] = [
            {
                "computername": "server01",
                "domainname": "example.com",
                "os_type": "linux",
                "environment": "prod",
            }
        ]

        inventory_plugin._populate_inventory(results)

        inventory_plugin.inventory.add_host.assert_called_once_with(
            "server01.example.com"
        )
        inventory_plugin.inventory.set_variable.assert_any_call(
            "server01.example.com", "os_type", "linux"
        )
        inventory_plugin.inventory.set_variable.assert_any_call(
            "server01.example.com", "environment", "prod"
        )
        inventory_plugin.inventory.set_variable.assert_any_call(
            "server01.example.com", "computername", "server01"
        )
        inventory_plugin.inventory.set_variable.assert_any_call(
            "server01.example.com", "domainname", "example.com"
        )

    def test_populate_inventory_multiple_hosts(
        self, inventory_plugin: InventoryModule
    ) -> None:
        """Test populating inventory with multiple hosts."""
        inventory_plugin._options = {
            "strict": False,
            "compose": {},
            "groups": {},
            "keyed_groups": [],
            "var_prefix": "",
        }
        inventory_plugin._set_composite_vars = MagicMock()  # type: ignore[method-assign]
        inventory_plugin._add_host_to_composed_groups = MagicMock()  # type: ignore[method-assign]
        inventory_plugin._add_host_to_keyed_groups = MagicMock()  # type: ignore[method-assign]

        results: list[dict[str, Any]] = [
            {"computername": "server01", "domainname": "example.com"},
            {"computername": "server02", "domainname": "example.com"},
            {"computername": "server03", "domainname": "other.com"},
        ]

        inventory_plugin._populate_inventory(results)

        assert inventory_plugin.inventory.add_host.call_count == 3

    def test_populate_inventory_with_var_prefix(
        self, inventory_plugin: InventoryModule
    ) -> None:
        """Test populating inventory with a variable prefix."""
        inventory_plugin._options = {
            "strict": False,
            "compose": {},
            "groups": {},
            "keyed_groups": [],
            "var_prefix": "restapi_",
        }
        inventory_plugin._set_composite_vars = MagicMock()  # type: ignore[method-assign]
        inventory_plugin._add_host_to_composed_groups = MagicMock()  # type: ignore[method-assign]
        inventory_plugin._add_host_to_keyed_groups = MagicMock()  # type: ignore[method-assign]

        results: list[dict[str, Any]] = [
            {
                "computername": "server01",
                "domainname": "example.com",
                "os_type": "linux",
            }
        ]

        inventory_plugin._populate_inventory(results)

        inventory_plugin.inventory.add_host.assert_called_once_with(
            "server01.example.com"
        )
        # All variables should have the prefix
        inventory_plugin.inventory.set_variable.assert_any_call(
            "server01.example.com", "restapi_os_type", "linux"
        )
        inventory_plugin.inventory.set_variable.assert_any_call(
            "server01.example.com", "restapi_computername", "server01"
        )
        inventory_plugin.inventory.set_variable.assert_any_call(
            "server01.example.com", "restapi_domainname", "example.com"
        )

    def test_populate_inventory_strips_whitespace(
        self, inventory_plugin: InventoryModule
    ) -> None:
        """Test that whitespace is stripped from string values."""
        inventory_plugin._options = {
            "strict": False,
            "compose": {},
            "groups": {},
            "keyed_groups": [],
            "var_prefix": "",
        }
        inventory_plugin._set_composite_vars = MagicMock()  # type: ignore[method-assign]
        inventory_plugin._add_host_to_composed_groups = MagicMock()  # type: ignore[method-assign]
        inventory_plugin._add_host_to_keyed_groups = MagicMock()  # type: ignore[method-assign]

        results: list[dict[str, Any]] = [
            {
                "computername": "server01  ",
                "domainname": "  example.com",
                "os_type": "  linux  ",
            }
        ]

        inventory_plugin._populate_inventory(results)

        inventory_plugin.inventory.add_host.assert_called_once_with(
            "server01.example.com"
        )
        inventory_plugin.inventory.set_variable.assert_any_call(
            "server01.example.com", "os_type", "linux"
        )

    def test_populate_inventory_skips_invalid_rows(
        self, inventory_plugin: InventoryModule
    ) -> None:
        """Test that invalid rows are skipped."""
        inventory_plugin._options = {
            "strict": False,
            "compose": {},
            "groups": {},
            "keyed_groups": [],
            "var_prefix": "",
        }
        inventory_plugin._set_composite_vars = MagicMock()  # type: ignore[method-assign]
        inventory_plugin._add_host_to_composed_groups = MagicMock()  # type: ignore[method-assign]
        inventory_plugin._add_host_to_keyed_groups = MagicMock()  # type: ignore[method-assign]

        results: list[dict[str, Any]] = [
            {"computername": "server01", "domainname": "example.com"},
            {"computername": "", "domainname": "example.com"},  # Invalid - empty computername
            {"computername": "server03", "domainname": "example.com"},
        ]

        inventory_plugin._populate_inventory(results)

        # Only 2 hosts should be added (the invalid one is skipped)
        assert inventory_plugin.inventory.add_host.call_count == 2


class TestPluginName:
    """Tests for the plugin NAME attribute."""

    def test_plugin_name(self, inventory_plugin: InventoryModule) -> None:
        """Test that the plugin has the correct name."""
        assert inventory_plugin.NAME == "ib_pf_ms_bhr.inv_plugins.restapi"
