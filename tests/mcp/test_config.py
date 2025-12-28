"""Tests for MCP configuration."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from code_forge.config.models import TransportType
from code_forge.mcp.config import (
    MCPConfig,
    MCPConfigLoader,
    MCPServerConfig,
    MCPSettings,
)


class TestMCPServerConfig:
    """Tests for MCPServerConfig."""

    def test_stdio_config(self) -> None:
        """Test stdio server configuration."""
        config = MCPServerConfig(
            name="test-server",
            transport=TransportType.STDIO,
            command="python",
            args=["-m", "mcp_server"],
        )
        assert config.name == "test-server"
        assert config.transport == TransportType.STDIO
        assert config.command == "python"
        assert config.args == ["-m", "mcp_server"]

    def test_http_config(self) -> None:
        """Test HTTP server configuration."""
        config = MCPServerConfig(
            name="remote-server",
            transport=TransportType.STREAMABLE_HTTP,
            url="https://example.com/mcp",
            headers={"Authorization": "Bearer token"},
        )
        assert config.name == "remote-server"
        assert config.transport == TransportType.STREAMABLE_HTTP
        assert config.url == "https://example.com/mcp"
        assert config.headers == {"Authorization": "Bearer token"}

    def test_defaults(self) -> None:
        """Test default values."""
        config = MCPServerConfig(
            name="test",
            transport=TransportType.STDIO,
            command="test",
        )
        assert config.enabled is True
        assert config.auto_connect is True
        assert config.args == []  # Pydantic defaults to empty list
        assert config.env == {}  # Pydantic defaults to empty dict
        assert config.cwd is None

    def test_model_validate(self) -> None:
        """Test creation with model_validate."""
        data = {
            "name": "test-server",
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@anthropic/mcp-filesystem"],
            "env": {"DEBUG": "true"},
            "cwd": "/tmp",
            "enabled": True,
            "auto_connect": False,
        }
        config = MCPServerConfig.model_validate(data)
        assert config.name == "test-server"
        assert config.command == "npx"
        assert config.args == ["-y", "@anthropic/mcp-filesystem"]
        assert config.env == {"DEBUG": "true"}
        assert config.cwd == "/tmp"
        assert config.auto_connect is False

    def test_model_dump(self) -> None:
        """Test conversion to dictionary with model_dump."""
        config = MCPServerConfig(
            name="test",
            transport=TransportType.STDIO,
            command="python",
            args=["-m", "server"],
            env={"KEY": "value"},
            cwd="/home",
            enabled=True,
            auto_connect=True,
        )
        d = config.model_dump()
        assert d["transport"] == TransportType.STDIO
        assert d["command"] == "python"
        assert d["args"] == ["-m", "server"]
        assert d["env"] == {"KEY": "value"}
        assert d["cwd"] == "/home"
        assert d["enabled"] is True
        assert d["auto_connect"] is True


class TestMCPSettings:
    """Tests for MCPSettings."""

    def test_defaults(self) -> None:
        """Test default values."""
        settings = MCPSettings()
        assert settings.auto_connect is True
        assert settings.reconnect_attempts == 3
        assert settings.reconnect_delay == 5
        assert settings.timeout == 30

    def test_custom_values(self) -> None:
        """Test custom values."""
        settings = MCPSettings(
            auto_connect=False,
            reconnect_attempts=5,
            reconnect_delay=10,
            timeout=60,
        )
        assert settings.auto_connect is False
        assert settings.reconnect_attempts == 5
        assert settings.reconnect_delay == 10
        assert settings.timeout == 60

    def test_model_validate(self) -> None:
        """Test creation with model_validate."""
        data = {
            "auto_connect": False,
            "reconnect_attempts": 5,
            "timeout": 60,
        }
        settings = MCPSettings.model_validate(data)
        assert settings.auto_connect is False
        assert settings.reconnect_attempts == 5
        assert settings.reconnect_delay == 5  # Default
        assert settings.timeout == 60

    def test_model_dump(self) -> None:
        """Test conversion to dictionary with model_dump."""
        settings = MCPSettings(
            auto_connect=False,
            reconnect_attempts=10,
            reconnect_delay=15,
            timeout=120,
        )
        d = settings.model_dump()
        assert d["auto_connect"] is False
        assert d["reconnect_attempts"] == 10
        assert d["reconnect_delay"] == 15
        assert d["timeout"] == 120


class TestMCPConfig:
    """Tests for MCPConfig."""

    def test_empty_config(self) -> None:
        """Test empty configuration."""
        config = MCPConfig()
        assert config.servers == {}
        assert config.settings.auto_connect is True

    def test_model_dump(self) -> None:
        """Test conversion to dictionary with model_dump."""
        config = MCPConfig(
            servers={
                "test": MCPServerConfig(
                    name="test",
                    transport=TransportType.STDIO,
                    command="python",
                )
            },
            settings=MCPSettings(timeout=45),
        )
        d = config.model_dump()
        assert "test" in d["servers"]
        assert d["settings"]["timeout"] == 45

    def test_get_enabled_servers(self) -> None:
        """Test getting enabled servers."""
        config = MCPConfig(
            servers={
                "enabled1": MCPServerConfig(
                    name="enabled1",
                    transport=TransportType.STDIO,
                    command="test",
                    enabled=True,
                ),
                "disabled": MCPServerConfig(
                    name="disabled",
                    transport=TransportType.STDIO,
                    command="test",
                    enabled=False,
                ),
                "enabled2": MCPServerConfig(
                    name="enabled2",
                    transport=TransportType.STREAMABLE_HTTP,
                    url="https://example.com",
                    enabled=True,
                ),
            }
        )
        enabled = config.get_enabled_servers()
        assert len(enabled) == 2
        names = [s.name for s in enabled]
        assert "enabled1" in names
        assert "enabled2" in names

    def test_get_auto_connect_servers(self) -> None:
        """Test getting auto-connect servers."""
        config = MCPConfig(
            servers={
                "auto1": MCPServerConfig(
                    name="auto1",
                    transport=TransportType.STDIO,
                    command="test",
                    enabled=True,
                    auto_connect=True,
                ),
                "manual": MCPServerConfig(
                    name="manual",
                    transport=TransportType.STDIO,
                    command="test",
                    enabled=True,
                    auto_connect=False,
                ),
                "disabled": MCPServerConfig(
                    name="disabled",
                    transport=TransportType.STDIO,
                    command="test",
                    enabled=False,
                    auto_connect=True,
                ),
            },
            settings=MCPSettings(auto_connect=True),
        )
        auto = config.get_auto_connect_servers()
        assert len(auto) == 1
        assert auto[0].name == "auto1"

    def test_get_auto_connect_respects_global_setting(self) -> None:
        """Test that global auto_connect setting is respected."""
        config = MCPConfig(
            servers={
                "test": MCPServerConfig(
                    name="test",
                    transport=TransportType.STDIO,
                    command="test",
                    enabled=True,
                    auto_connect=True,
                ),
            },
            settings=MCPSettings(auto_connect=False),
        )
        auto = config.get_auto_connect_servers()
        assert len(auto) == 0


class TestMCPConfigLoader:
    """Tests for MCPConfigLoader."""

    def test_default_paths(self) -> None:
        """Test default configuration paths."""
        loader = MCPConfigLoader()
        assert loader.user_path == Path.home() / ".forge" / "mcp.yaml"
        assert loader.project_path == Path(".forge") / "mcp.yaml"

    def test_custom_paths(self) -> None:
        """Test custom configuration paths."""
        loader = MCPConfigLoader(
            user_path=Path("/custom/user.yaml"),
            project_path=Path("/custom/project.yaml"),
        )
        assert loader.user_path == Path("/custom/user.yaml")
        assert loader.project_path == Path("/custom/project.yaml")

    def test_load_no_files(self) -> None:
        """Test loading when no config files exist."""
        loader = MCPConfigLoader(
            user_path=Path("/nonexistent/user.yaml"),
            project_path=Path("/nonexistent/project.yaml"),
        )
        config = loader.load()
        assert config.servers == {}

    def test_load_from_file(self) -> None:
        """Test loading from a file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(
                {
                    "servers": {
                        "test": {
                            "transport": "stdio",
                            "command": "python",
                        }
                    }
                },
                f,
            )
            f.flush()

            try:
                loader = MCPConfigLoader()
                config = loader.load_from_file(Path(f.name))
                assert "test" in config.servers
                assert config.servers["test"].command == "python"
            finally:
                os.unlink(f.name)

    def test_load_from_file_with_env_vars(self) -> None:
        """Test environment variable expansion."""
        os.environ["TEST_MCP_KEY"] = "secret123"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(
                {
                    "servers": {
                        "test": {
                            "transport": "http",
                            "url": "https://example.com",
                            "headers": {"Authorization": "Bearer ${TEST_MCP_KEY}"},
                        }
                    }
                },
                f,
            )
            f.flush()

            try:
                loader = MCPConfigLoader()
                config = loader.load_from_file(Path(f.name))
                assert isinstance(config.servers["test"].headers, dict)
                assert config.servers["test"].headers["Authorization"] == "Bearer secret123"
            finally:
                os.unlink(f.name)
                del os.environ["TEST_MCP_KEY"]

    def test_merge_configs(self) -> None:
        """Test merging multiple configurations."""
        loader = MCPConfigLoader()

        config1 = MCPConfig(
            servers={
                "server1": MCPServerConfig(
                    name="server1",
                    transport=TransportType.STDIO,
                    command="cmd1",
                )
            },
            settings=MCPSettings(timeout=30),
        )

        config2 = MCPConfig(
            servers={
                "server2": MCPServerConfig(
                    name="server2",
                    transport=TransportType.STREAMABLE_HTTP,
                    url="https://example.com",
                )
            },
            settings=MCPSettings(timeout=60),
        )

        merged = loader.merge_configs(config1, config2)

        assert len(merged.servers) == 2
        assert "server1" in merged.servers
        assert "server2" in merged.servers
        assert merged.settings.timeout == 60  # Later overrides

    def test_merge_configs_override(self) -> None:
        """Test that later configs override earlier ones."""
        loader = MCPConfigLoader()

        config1 = MCPConfig(
            servers={
                "shared": MCPServerConfig(
                    name="shared",
                    transport=TransportType.STDIO,
                    command="old",
                )
            }
        )

        config2 = MCPConfig(
            servers={
                "shared": MCPServerConfig(
                    name="shared",
                    transport=TransportType.STDIO,
                    command="new",
                )
            }
        )

        merged = loader.merge_configs(config1, config2)
        assert merged.servers["shared"].command == "new"

    def test_load_merges_user_and_project(self) -> None:
        """Test that load merges user and project configs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_path = Path(tmpdir) / "user.yaml"
            project_path = Path(tmpdir) / "project.yaml"

            with open(user_path, "w") as f:
                yaml.dump(
                    {
                        "servers": {
                            "user-server": {
                                "transport": "stdio",
                                "command": "user-cmd",
                            }
                        }
                    },
                    f,
                )

            with open(project_path, "w") as f:
                yaml.dump(
                    {
                        "servers": {
                            "project-server": {
                                "transport": "http",
                                "url": "https://project.com",
                            }
                        }
                    },
                    f,
                )

            loader = MCPConfigLoader(
                user_path=user_path,
                project_path=project_path,
            )
            config = loader.load()

            assert len(config.servers) == 2
            assert "user-server" in config.servers
            assert "project-server" in config.servers

    def test_save_to_file(self) -> None:
        """Test saving configuration to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mcp.yaml"

            config = MCPConfig(
                servers={
                    "test": MCPServerConfig(
                        name="test",
                        transport=TransportType.STDIO,
                        command="test-cmd",
                    )
                }
            )

            loader = MCPConfigLoader()
            # Patch ALLOWED_SAVE_DIRS to include temp directory
            original_dirs = MCPConfigLoader.ALLOWED_SAVE_DIRS
            MCPConfigLoader.ALLOWED_SAVE_DIRS = [Path(tmpdir)]
            try:
                loader.save_to_file(config, path)

                # Reload and verify
                loaded = loader.load_from_file(path)
                assert "test" in loaded.servers
                assert loaded.servers["test"].command == "test-cmd"
            finally:
                MCPConfigLoader.ALLOWED_SAVE_DIRS = original_dirs

    def test_save_creates_directories(self) -> None:
        """Test that save creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nested" / "dir" / "mcp.yaml"

            config = MCPConfig()
            loader = MCPConfigLoader()
            # Patch ALLOWED_SAVE_DIRS to include temp directory
            original_dirs = MCPConfigLoader.ALLOWED_SAVE_DIRS
            MCPConfigLoader.ALLOWED_SAVE_DIRS = [Path(tmpdir)]
            try:
                loader.save_to_file(config, path)
                assert path.exists()
            finally:
                MCPConfigLoader.ALLOWED_SAVE_DIRS = original_dirs

    def test_expand_env_vars_nested(self) -> None:
        """Test environment variable expansion in nested structures."""
        os.environ["TEST_VAR"] = "value"

        try:
            loader = MCPConfigLoader()
            data = {
                "level1": {
                    "level2": "${TEST_VAR}",
                    "list": ["${TEST_VAR}", "static"],
                }
            }
            expanded = loader._expand_env_vars(data)
            assert expanded["level1"]["level2"] == "value"
            assert expanded["level1"]["list"][0] == "value"
            assert expanded["level1"]["list"][1] == "static"
        finally:
            del os.environ["TEST_VAR"]

    def test_load_handles_empty_file(self) -> None:
        """Test loading an empty YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")  # Empty file
            f.flush()

            try:
                loader = MCPConfigLoader()
                config = loader.load_from_file(Path(f.name))
                assert config.servers == {}
            finally:
                os.unlink(f.name)

    def test_load_handles_invalid_yaml_gracefully(self) -> None:
        """Test that invalid YAML is handled gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create an invalid YAML file
            bad_path = Path(tmpdir) / "bad.yaml"
            with open(bad_path, "w") as f:
                f.write("this: is: not: valid: yaml: [[[")

            loader = MCPConfigLoader(
                user_path=bad_path,
                project_path=Path("/nonexistent"),
            )

            # Should return empty config on error
            config = loader.load()
            # The loader logs a warning but returns empty config
            assert isinstance(config, MCPConfig)
            assert config.servers == {}
