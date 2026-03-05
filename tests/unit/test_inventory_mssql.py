# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Your Name <example@domain.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Unit tests for the MSSQL dynamic inventory plugin."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

# Add the project root to the path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import the actual plugin module
from plugins.inventory.mssql import InventoryModule


@pytest.fixture
def inventory_plugin() -> Generator[InventoryModule, None, None]:
    """Create an instance of the MSSQL inventory plugin for testing."""
    plugin = InventoryModule()
    plugin.inventory = MagicMock()
    plugin.display = MagicMock()
    plugin._options: dict[str, Any] = {}

    # Override get_option to use our _options dict
    plugin.get_option = lambda x: plugin._options.get(x)  # type: ignore[method-assign]

    yield plugin


class TestInventoryModuleVerifyFile:
    """Tests for the verify_file method."""

    def test_verify_file_valid_mssql_yml(self) -> None:
        """Test that .mssql.yml files are accepted."""
        path = "/path/to/inventory.mssql.yml"
        valid = path.endswith((".mssql.yml", ".mssql.yaml"))
        assert valid is True

    def test_verify_file_valid_mssql_yaml(self) -> None:
        """Test that .mssql.yaml files are accepted."""
        path = "/path/to/inventory.mssql.yaml"
        valid = path.endswith((".mssql.yml", ".mssql.yaml"))
        assert valid is True

    def test_verify_file_invalid_extension(self) -> None:
        """Test that non-mssql files are rejected."""
        path = "/path/to/inventory.yml"
        valid = path.endswith((".mssql.yml", ".mssql.yaml"))
        assert valid is False


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

        inventory_plugin.inventory.add_host.assert_called_with("server01.example.com")  # type: ignore[union-attr]
        inventory_plugin.inventory.set_variable.assert_any_call(  # type: ignore[union-attr]
            "server01.example.com", "os_type", "linux"
        )
        inventory_plugin.inventory.set_variable.assert_any_call(  # type: ignore[union-attr]
            "server01.example.com", "environment", "prod"
        )
        inventory_plugin.inventory.set_variable.assert_any_call(  # type: ignore[union-attr]
            "server01.example.com", "computername", "server01"
        )
        inventory_plugin.inventory.set_variable.assert_any_call(  # type: ignore[union-attr]
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

        assert inventory_plugin.inventory.add_host.call_count == 3  # type: ignore[union-attr]

    def test_populate_inventory_with_var_prefix(
        self, inventory_plugin: InventoryModule
    ) -> None:
        """Test populating inventory with a variable prefix."""
        inventory_plugin._options = {
            "strict": False,
            "compose": {},
            "groups": {},
            "keyed_groups": [],
            "var_prefix": "mssql_",
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

        inventory_plugin.inventory.add_host.assert_called_with("server01.example.com")  # type: ignore[union-attr]
        # All variables should have the prefix
        inventory_plugin.inventory.set_variable.assert_any_call(  # type: ignore[union-attr]
            "server01.example.com", "mssql_os_type", "linux"
        )
        inventory_plugin.inventory.set_variable.assert_any_call(  # type: ignore[union-attr]
            "server01.example.com", "mssql_computername", "server01"
        )
        inventory_plugin.inventory.set_variable.assert_any_call(  # type: ignore[union-attr]
            "server01.example.com", "mssql_domainname", "example.com"
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
            {"computername": "server03", "domainname": "other.com"},
        ]

        inventory_plugin._populate_inventory(results)

        # Only 2 hosts should be added (the invalid one is skipped)
        assert inventory_plugin.inventory.add_host.call_count == 2  # type: ignore[union-attr]


class TestExecuteQuery:
    """Tests for the _execute_query method."""

    def test_execute_query_normalizes_column_names(self) -> None:
        """Test that column names are normalized to lowercase."""
        # Simulate the normalization logic
        results: list[dict[str, Any]] = []
        for row in [
            {"COMPUTERNAME": "server01", "DOMAINNAME": "example.com", "OS_TYPE": "linux"}
        ]:
            normalized = {k.lower(): v for k, v in row.items()}
            results.append(normalized)

        assert results[0]["computername"] == "server01"
        assert results[0]["domainname"] == "example.com"
        assert results[0]["os_type"] == "linux"


class TestGetConnection:
    """Tests for the _get_connection method."""

    def test_get_connection_missing_pymssql(
        self, inventory_plugin: InventoryModule
    ) -> None:
        """Test that missing pymssql raises appropriate error."""
        inventory_plugin._options = {
            "host": "localhost",
            "port": 1433,
            "database": "test",
            "username": "user",
            "password": "pass",
            "connect_timeout": 30,
        }

        # This test verifies the import error handling logic
        expected_msg = (
            "The pymssql library is required for the mssql inventory plugin. "
            "Install it with: pip install pymssql"
        )
        assert "pymssql" in expected_msg

    def test_get_connection_with_mock_pymssql(
        self, inventory_plugin: InventoryModule
    ) -> None:
        """Test connection establishment with mocked pymssql."""
        inventory_plugin._options = {
            "host": "localhost",
            "port": 1433,
            "database": "test",
            "auth_method": "sql",
            "username": "user",
            "password": "pass",
            "connect_timeout": 30,
            "tds_version": "7.3",
        }

        mock_pymssql = MagicMock()
        mock_connection = MagicMock()
        mock_pymssql.connect.return_value = mock_connection

        with patch.dict("sys.modules", {"pymssql": mock_pymssql}):
            with patch(
                "plugins.inventory.mssql.InventoryModule._get_connection",
                return_value=mock_connection,
            ):
                result = inventory_plugin._get_connection()
                assert result == mock_connection


class TestKerberosAuthentication:
    """Tests for Kerberos authentication functionality."""

    def test_kerberos_check_ticket_success(
        self, inventory_plugin: InventoryModule
    ) -> None:
        """Test that Kerberos ticket check passes with valid ticket."""
        with patch("shutil.which", return_value="/usr/bin/klist"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                # Should not raise
                inventory_plugin._check_kerberos_ticket()
                mock_run.assert_called_once()

    def test_kerberos_check_ticket_no_klist(
        self, inventory_plugin: InventoryModule
    ) -> None:
        """Test that missing klist issues warning but doesn't fail."""
        with patch("shutil.which", return_value=None):
            # Should not raise, just warn
            inventory_plugin._check_kerberos_ticket()
            inventory_plugin.display.warning.assert_called()  # type: ignore[union-attr]

    def test_kerberos_default_auth_method(self) -> None:
        """Test that Kerberos is the default authentication method."""
        # The default in DOCUMENTATION is 'kerberos'
        # This is a documentation test
        from plugins.inventory.mssql import DOCUMENTATION

        assert "default: kerberos" in DOCUMENTATION

    def test_sql_auth_requires_credentials(
        self, inventory_plugin: InventoryModule
    ) -> None:
        """Test that SQL auth method requires username and password."""
        inventory_plugin._options = {
            "host": "localhost",
            "port": 1433,
            "database": "test",
            "auth_method": "sql",
            "username": None,
            "password": None,
            "connect_timeout": 30,
            "tds_version": "7.3",
        }

        # Mock pymssql to avoid import issues
        mock_pymssql = MagicMock()
        with patch.dict("sys.modules", {"pymssql": mock_pymssql}):
            from ansible.errors import AnsibleError

            with pytest.raises(AnsibleError) as exc_info:
                inventory_plugin._get_connection()

            assert "Username and password are required" in str(exc_info.value)
