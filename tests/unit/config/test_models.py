"""Tests for configuration models."""

from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from code_forge.config.models import (
    DisplayConfig,
    HookConfig,
    HooksConfig,
    HookType,
    MCPServerConfig,
    ModelConfig,
    CodeForgeConfig,
    PermissionConfig,
    RoutingVariant,
    SessionConfig,
    TransportType,
)


class TestModelConfig:
    """Tests for ModelConfig."""

    def test_default_values(self) -> None:
        """Test default values are set correctly."""
        config = ModelConfig()
        assert config.default == "anthropic/claude-3.5-sonnet"
        assert "openai/gpt-4o" in config.fallback
        assert config.max_tokens == 8192
        assert config.temperature == 1.0
        assert config.routing_variant is None

    def test_custom_values(self) -> None:
        """Test custom values are accepted."""
        config = ModelConfig(
            default="custom-model",
            fallback=["model-a", "model-b"],
            max_tokens=4096,
            temperature=0.5,
            routing_variant=RoutingVariant.NITRO,
        )
        assert config.default == "custom-model"
        assert config.fallback == ["model-a", "model-b"]
        assert config.max_tokens == 4096
        assert config.temperature == 0.5
        assert config.routing_variant == RoutingVariant.NITRO

    def test_max_tokens_minimum(self) -> None:
        """Test max_tokens minimum validation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelConfig(max_tokens=0)
        assert "max_tokens" in str(exc_info.value)

    def test_max_tokens_maximum(self) -> None:
        """Test max_tokens maximum validation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelConfig(max_tokens=500000)
        assert "max_tokens" in str(exc_info.value)

    def test_temperature_minimum(self) -> None:
        """Test temperature minimum validation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelConfig(temperature=-0.1)
        assert "temperature" in str(exc_info.value)

    def test_temperature_maximum(self) -> None:
        """Test temperature maximum validation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelConfig(temperature=2.5)
        assert "temperature" in str(exc_info.value)

    def test_empty_model_name_rejected(self) -> None:
        """Test empty model name is rejected."""
        with pytest.raises(ValidationError):
            ModelConfig(default="")

    def test_whitespace_model_name_rejected(self) -> None:
        """Test whitespace-only model name is rejected."""
        with pytest.raises(ValidationError):
            ModelConfig(default="   ")

    def test_model_name_stripped(self) -> None:
        """Test model name whitespace is stripped."""
        config = ModelConfig(default="  model-name  ")
        assert config.default == "model-name"


class TestRoutingVariant:
    """Tests for RoutingVariant enum."""

    def test_all_variants_exist(self) -> None:
        """Test all routing variants are defined."""
        assert RoutingVariant.NITRO.value == "nitro"
        assert RoutingVariant.FLOOR.value == "floor"
        assert RoutingVariant.EXACTO.value == "exacto"
        assert RoutingVariant.THINKING.value == "thinking"
        assert RoutingVariant.ONLINE.value == "online"

    def test_variant_from_string(self) -> None:
        """Test variant can be created from string."""
        config = ModelConfig(routing_variant="nitro")  # type: ignore[arg-type]
        assert config.routing_variant == RoutingVariant.NITRO


class TestPermissionConfig:
    """Tests for PermissionConfig."""

    def test_default_empty_lists(self) -> None:
        """Test default lists are empty."""
        config = PermissionConfig()
        assert config.allow == []
        assert config.ask == []
        assert config.deny == []

    def test_custom_patterns(self) -> None:
        """Test custom permission patterns."""
        config = PermissionConfig(
            allow=["Read(*)", "Glob(*)"],
            ask=["Write(*)"],
            deny=["Bash(rm -rf:*)"],
        )
        assert "Read(*)" in config.allow
        assert "Write(*)" in config.ask
        assert "Bash(rm -rf:*)" in config.deny


class TestHookConfig:
    """Tests for HookConfig."""

    def test_command_hook(self) -> None:
        """Test command hook configuration."""
        hook = HookConfig(
            type=HookType.COMMAND,
            matcher="Bash(*)",
            command="echo 'pre-hook'",
            timeout=30,
        )
        assert hook.type == HookType.COMMAND
        assert hook.command == "echo 'pre-hook'"
        assert hook.timeout == 30

    def test_prompt_hook(self) -> None:
        """Test prompt hook configuration."""
        hook = HookConfig(
            type=HookType.PROMPT,
            matcher="Write(*)",
            prompt="Please review carefully.",
        )
        assert hook.type == HookType.PROMPT
        assert hook.prompt == "Please review carefully."

    def test_timeout_minimum(self) -> None:
        """Test timeout minimum validation."""
        with pytest.raises(ValidationError):
            HookConfig(type=HookType.COMMAND, timeout=0)

    def test_timeout_maximum(self) -> None:
        """Test timeout maximum validation."""
        with pytest.raises(ValidationError):
            HookConfig(type=HookType.COMMAND, timeout=400)

    def test_hook_content_stripped(self) -> None:
        """Test hook content whitespace is stripped."""
        hook = HookConfig(type=HookType.COMMAND, command="  echo test  ")
        assert hook.command == "echo test"

    def test_empty_command_becomes_none(self) -> None:
        """Test empty command becomes None."""
        hook = HookConfig(type=HookType.COMMAND, command="   ")
        assert hook.command is None


class TestHooksConfig:
    """Tests for HooksConfig."""

    def test_default_empty_lists(self) -> None:
        """Test all hook lists are empty by default."""
        config = HooksConfig()
        assert config.pre_tool_use == []
        assert config.post_tool_use == []
        assert config.user_prompt_submit == []
        assert config.stop == []
        assert config.subagent_stop == []
        assert config.notification == []

    def test_add_hooks(self) -> None:
        """Test adding hooks to configuration."""
        hook = HookConfig(type=HookType.COMMAND, command="echo test")
        config = HooksConfig(pre_tool_use=[hook])
        assert len(config.pre_tool_use) == 1
        assert config.pre_tool_use[0].command == "echo test"


class TestMCPServerConfig:
    """Tests for MCPServerConfig."""

    def test_stdio_transport(self) -> None:
        """Test stdio transport configuration."""
        config = MCPServerConfig(
            transport=TransportType.STDIO,
            command="python",
            args=["-m", "my_server"],
            env={"DEBUG": "1"},
        )
        assert config.transport == TransportType.STDIO
        assert config.command == "python"
        assert config.args == ["-m", "my_server"]
        assert config.env == {"DEBUG": "1"}

    def test_http_transport(self) -> None:
        """Test HTTP transport configuration."""
        config = MCPServerConfig(
            transport=TransportType.STREAMABLE_HTTP,
            url="https://mcp.example.com",
            oauth_client_id="client-123",
        )
        assert config.transport == TransportType.STREAMABLE_HTTP
        assert config.url == "https://mcp.example.com"
        assert config.oauth_client_id == "client-123"

    def test_transport_enum_values(self) -> None:
        """Test transport enum values."""
        assert TransportType.STDIO.value == "stdio"
        assert TransportType.STREAMABLE_HTTP.value == "streamable-http"


class TestDisplayConfig:
    """Tests for DisplayConfig."""

    def test_default_values(self) -> None:
        """Test default display values."""
        config = DisplayConfig()
        assert config.theme == "dark"
        assert config.show_tokens is True
        assert config.show_cost is True
        assert config.streaming is True
        assert config.vim_mode is False
        assert config.status_line is True
        assert config.color is True
        assert config.quiet is False
        assert config.json_output is False

    def test_custom_values(self) -> None:
        """Test custom display values."""
        config = DisplayConfig(
            theme="light",
            show_tokens=False,
            vim_mode=True,
        )
        assert config.theme == "light"
        assert config.show_tokens is False
        assert config.vim_mode is True

    def test_theme_normalized(self) -> None:
        """Test theme is normalized to lowercase."""
        config = DisplayConfig(theme="DARK")
        assert config.theme == "dark"

    def test_output_format_options(self) -> None:
        """Test output format options (color, quiet, json_output)."""
        config = DisplayConfig(
            color=False,
            quiet=True,
            json_output=True,
        )
        assert config.color is False
        assert config.quiet is True
        assert config.json_output is True


class TestSessionConfig:
    """Tests for SessionConfig."""

    def test_default_values(self) -> None:
        """Test default session values."""
        config = SessionConfig()
        assert config.auto_save is True
        assert config.save_interval == 60
        assert config.max_history == 100
        assert config.session_dir is None
        assert config.compress_after == 50

    def test_custom_values(self) -> None:
        """Test custom session values."""
        config = SessionConfig(
            auto_save=False,
            save_interval=120,
            max_history=500,
            session_dir=Path("/tmp/sessions"),
            compress_after=100,
        )
        assert config.auto_save is False
        assert config.save_interval == 120
        assert config.max_history == 500
        assert config.session_dir == Path("/tmp/sessions")
        assert config.compress_after == 100

    def test_save_interval_minimum(self) -> None:
        """Test save_interval minimum validation."""
        with pytest.raises(ValidationError):
            SessionConfig(save_interval=5)

    def test_save_interval_maximum(self) -> None:
        """Test save_interval maximum validation."""
        with pytest.raises(ValidationError):
            SessionConfig(save_interval=4000)

    def test_max_history_minimum(self) -> None:
        """Test max_history minimum validation."""
        with pytest.raises(ValidationError):
            SessionConfig(max_history=0)

    def test_max_history_maximum(self) -> None:
        """Test max_history maximum validation."""
        with pytest.raises(ValidationError):
            SessionConfig(max_history=20000)


class TestCodeForgeConfig:
    """Tests for CodeForgeConfig."""

    def test_default_values(self) -> None:
        """Test default root config values."""
        config = CodeForgeConfig()
        assert config.model.default == "anthropic/claude-3.5-sonnet"
        assert config.display.theme == "dark"
        assert config.api_key is None

    def test_nested_config(self) -> None:
        """Test nested configuration."""
        config = CodeForgeConfig(
            model=ModelConfig(default="custom-model"),
            display=DisplayConfig(theme="light"),
        )
        assert config.model.default == "custom-model"
        assert config.display.theme == "light"

    def test_api_key_is_secret(self) -> None:
        """Test API key is stored as SecretStr."""
        config = CodeForgeConfig(api_key="sk-secret-123")  # type: ignore[arg-type]
        assert isinstance(config.api_key, SecretStr)

    def test_api_key_not_in_repr(self) -> None:
        """Test API key is not exposed in repr."""
        config = CodeForgeConfig(api_key="sk-secret-123")  # type: ignore[arg-type]
        repr_str = repr(config)
        assert "sk-secret-123" not in repr_str

    def test_api_key_not_in_str(self) -> None:
        """Test API key is not exposed in str."""
        config = CodeForgeConfig(api_key="sk-secret-123")  # type: ignore[arg-type]
        str_repr = str(config)
        assert "sk-secret-123" not in str_repr

    def test_get_api_key(self) -> None:
        """Test get_api_key returns the value."""
        config = CodeForgeConfig(api_key="sk-secret-123")  # type: ignore[arg-type]
        assert config.get_api_key() == "sk-secret-123"

    def test_get_api_key_none(self) -> None:
        """Test get_api_key returns None when not set."""
        config = CodeForgeConfig()
        assert config.get_api_key() is None

    def test_extra_fields_ignored(self) -> None:
        """Test extra fields are ignored."""
        # Should not raise
        config = CodeForgeConfig.model_validate({"unknown_field": "value"})
        assert not hasattr(config, "unknown_field")

    def test_mcp_servers(self) -> None:
        """Test MCP servers configuration."""
        config = CodeForgeConfig(
            mcp_servers={
                "my-server": MCPServerConfig(
                    transport=TransportType.STDIO,
                    command="python",
                    args=["-m", "server"],
                )
            }
        )
        assert "my-server" in config.mcp_servers
        assert config.mcp_servers["my-server"].command == "python"

    def test_validate_assignment(self) -> None:
        """Test validation on assignment."""
        config = CodeForgeConfig()
        with pytest.raises(ValidationError):
            config.model.max_tokens = 500000  # type: ignore[assignment]


class TestHookType:
    """Tests for HookType enum."""

    def test_hook_types(self) -> None:
        """Test hook type values."""
        assert HookType.COMMAND.value == "command"
        assert HookType.PROMPT.value == "prompt"
