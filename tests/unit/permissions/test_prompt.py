"""Unit tests for permission prompts."""

import pytest
import asyncio
from unittest.mock import MagicMock, patch

from code_forge.permissions.models import (
    PermissionLevel,
    PermissionRule,
)
from code_forge.permissions.prompt import (
    ConfirmationChoice,
    ConfirmationRequest,
    PermissionPrompt,
    create_rule_from_choice,
)


@pytest.fixture
def event_loop():
    """Create an event loop for async tests (fixes WSL source code issue)."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


class TestConfirmationChoice:
    """Tests for ConfirmationChoice enum."""

    def test_values(self):
        """Test that all expected values exist."""
        assert ConfirmationChoice.ALLOW.value == "allow"
        assert ConfirmationChoice.ALLOW_ALWAYS.value == "allow_always"
        assert ConfirmationChoice.DENY.value == "deny"
        assert ConfirmationChoice.DENY_ALWAYS.value == "deny_always"
        assert ConfirmationChoice.TIMEOUT.value == "timeout"


class TestConfirmationRequest:
    """Tests for ConfirmationRequest dataclass."""

    def test_creation_minimal(self):
        """Test creating request with minimal arguments."""
        request = ConfirmationRequest(
            tool_name="bash",
            arguments={"command": "ls"},
        )
        assert request.tool_name == "bash"
        assert request.arguments == {"command": "ls"}
        assert request.description == ""
        assert request.timeout == 30.0

    def test_creation_full(self):
        """Test creating request with all arguments."""
        request = ConfirmationRequest(
            tool_name="bash",
            arguments={"command": "ls"},
            description="List directory",
            timeout=60.0,
        )
        assert request.tool_name == "bash"
        assert request.description == "List directory"
        assert request.timeout == 60.0


class TestPermissionPrompt:
    """Tests for PermissionPrompt class."""

    def test_creation_default_handlers(self):
        """Test creating prompt with default handlers."""
        prompt = PermissionPrompt()
        assert prompt.input_handler is input
        assert prompt.output_handler is print

    def test_creation_custom_handlers(self):
        """Test creating prompt with custom handlers."""
        mock_input = MagicMock(return_value="a")
        mock_output = MagicMock()

        prompt = PermissionPrompt(
            input_handler=mock_input, output_handler=mock_output
        )
        assert prompt.input_handler is mock_input
        assert prompt.output_handler is mock_output


class TestPermissionPromptFormatRequest:
    """Tests for PermissionPrompt.format_request."""

    def test_format_basic_request(self):
        """Test formatting basic request."""
        prompt = PermissionPrompt()
        request = ConfirmationRequest(
            tool_name="bash",
            arguments={"command": "ls -la"},
        )

        formatted = prompt.format_request(request)

        assert "Permission Required" in formatted
        assert "bash" in formatted
        assert "ls -la" in formatted

    def test_format_with_description(self):
        """Test formatting request with description."""
        prompt = PermissionPrompt()
        request = ConfirmationRequest(
            tool_name="bash",
            arguments={"command": "ls"},
            description="List directory contents",
        )

        formatted = prompt.format_request(request)

        assert "List directory contents" in formatted

    def test_format_long_argument_truncated(self):
        """Test that long arguments are truncated."""
        prompt = PermissionPrompt()
        request = ConfirmationRequest(
            tool_name="bash",
            arguments={"command": "a" * 100},
        )

        formatted = prompt.format_request(request)

        assert "..." in formatted

    def test_format_shows_choices(self):
        """Test that format shows available choices."""
        prompt = PermissionPrompt()
        request = ConfirmationRequest(
            tool_name="bash",
            arguments={},
        )

        formatted = prompt.format_request(request)

        assert "[a] Allow" in formatted
        assert "[A] Allow Always" in formatted
        assert "[d] Deny" in formatted
        assert "[D] Deny Always" in formatted

    def test_format_multiple_arguments(self):
        """Test formatting request with multiple arguments."""
        prompt = PermissionPrompt()
        request = ConfirmationRequest(
            tool_name="write",
            arguments={
                "file_path": "/tmp/test.txt",
                "content": "Hello",
            },
        )

        formatted = prompt.format_request(request)

        assert "file_path" in formatted
        assert "/tmp/test.txt" in formatted


class TestPermissionPromptParseResponse:
    """Tests for PermissionPrompt._parse_response."""

    def test_parse_allow(self):
        """Test parsing 'a' as ALLOW."""
        prompt = PermissionPrompt()
        assert prompt._parse_response("a") == ConfirmationChoice.ALLOW

    def test_parse_allow_always(self):
        """Test parsing 'A' as ALLOW_ALWAYS."""
        prompt = PermissionPrompt()
        assert prompt._parse_response("A") == ConfirmationChoice.ALLOW_ALWAYS

    def test_parse_deny(self):
        """Test parsing 'd' as DENY."""
        prompt = PermissionPrompt()
        assert prompt._parse_response("d") == ConfirmationChoice.DENY

    def test_parse_deny_always(self):
        """Test parsing 'D' as DENY_ALWAYS."""
        prompt = PermissionPrompt()
        assert prompt._parse_response("D") == ConfirmationChoice.DENY_ALWAYS

    def test_parse_empty_defaults_to_deny(self):
        """Test that empty input defaults to DENY."""
        prompt = PermissionPrompt()
        assert prompt._parse_response("") == ConfirmationChoice.DENY

    def test_parse_invalid_defaults_to_deny(self):
        """Test that invalid input defaults to DENY."""
        prompt = PermissionPrompt()
        assert prompt._parse_response("x") == ConfirmationChoice.DENY
        assert prompt._parse_response("yes") == ConfirmationChoice.DENY
        assert prompt._parse_response("1") == ConfirmationChoice.DENY


class TestPermissionPromptConfirm:
    """Tests for PermissionPrompt.confirm (synchronous)."""

    def test_confirm_returns_allow(self):
        """Test confirm returns ALLOW for 'a' input."""
        mock_input = MagicMock(return_value="a")
        mock_output = MagicMock()
        prompt = PermissionPrompt(
            input_handler=mock_input, output_handler=mock_output
        )

        request = ConfirmationRequest(tool_name="bash", arguments={})
        choice = prompt.confirm(request)

        assert choice == ConfirmationChoice.ALLOW
        assert mock_output.called

    def test_confirm_returns_deny_on_eof(self):
        """Test confirm returns DENY on EOFError."""
        mock_input = MagicMock(side_effect=EOFError())
        mock_output = MagicMock()
        prompt = PermissionPrompt(
            input_handler=mock_input, output_handler=mock_output
        )

        request = ConfirmationRequest(tool_name="bash", arguments={})
        choice = prompt.confirm(request)

        assert choice == ConfirmationChoice.DENY

    def test_confirm_returns_deny_on_keyboard_interrupt(self):
        """Test confirm returns DENY on KeyboardInterrupt."""
        mock_input = MagicMock(side_effect=KeyboardInterrupt())
        mock_output = MagicMock()
        prompt = PermissionPrompt(
            input_handler=mock_input, output_handler=mock_output
        )

        request = ConfirmationRequest(tool_name="bash", arguments={})
        choice = prompt.confirm(request)

        assert choice == ConfirmationChoice.DENY

    def test_confirm_strips_whitespace(self):
        """Test that input is stripped of whitespace."""
        mock_input = MagicMock(return_value="  a  ")
        mock_output = MagicMock()
        prompt = PermissionPrompt(
            input_handler=mock_input, output_handler=mock_output
        )

        request = ConfirmationRequest(tool_name="bash", arguments={})
        choice = prompt.confirm(request)

        assert choice == ConfirmationChoice.ALLOW


class TestPermissionPromptConfirmAsync:
    """Tests for PermissionPrompt.confirm_async (asynchronous)."""

    @pytest.mark.asyncio
    async def test_confirm_async_returns_allow(self):
        """Test async confirm returns ALLOW for 'a' input."""
        mock_input = MagicMock(return_value="a")
        mock_output = MagicMock()
        prompt = PermissionPrompt(
            input_handler=mock_input, output_handler=mock_output
        )

        request = ConfirmationRequest(
            tool_name="bash", arguments={}, timeout=5.0
        )
        choice = await prompt.confirm_async(request)

        assert choice == ConfirmationChoice.ALLOW

    @pytest.mark.asyncio
    async def test_confirm_async_returns_timeout(self):
        """Test async confirm returns TIMEOUT on timeout."""
        # Use a blocking input that will be interrupted
        def slow_input(prompt_str):
            import time
            time.sleep(10)
            return "a"

        mock_output = MagicMock()
        prompt = PermissionPrompt(
            input_handler=slow_input, output_handler=mock_output
        )

        request = ConfirmationRequest(
            tool_name="bash", arguments={}, timeout=0.1
        )
        choice = await prompt.confirm_async(request)

        assert choice == ConfirmationChoice.TIMEOUT

    @pytest.mark.asyncio
    async def test_confirm_async_no_timeout(self):
        """Test async confirm with zero timeout uses sync path."""
        mock_input = MagicMock(return_value="A")
        mock_output = MagicMock()
        prompt = PermissionPrompt(
            input_handler=mock_input, output_handler=mock_output
        )

        request = ConfirmationRequest(
            tool_name="bash", arguments={}, timeout=0
        )
        choice = await prompt.confirm_async(request)

        assert choice == ConfirmationChoice.ALLOW_ALWAYS


class TestCreateRuleFromChoice:
    """Tests for create_rule_from_choice function."""

    def test_allow_always_creates_allow_rule(self):
        """Test ALLOW_ALWAYS creates ALLOW rule."""
        rule = create_rule_from_choice(
            ConfirmationChoice.ALLOW_ALWAYS, "bash", {}
        )

        assert isinstance(rule, PermissionRule)
        assert rule.pattern == "tool:bash"
        assert rule.permission == PermissionLevel.ALLOW
        assert rule.priority == 100

    def test_deny_always_creates_deny_rule(self):
        """Test DENY_ALWAYS creates DENY rule."""
        rule = create_rule_from_choice(
            ConfirmationChoice.DENY_ALWAYS, "bash", {}
        )

        assert isinstance(rule, PermissionRule)
        assert rule.pattern == "tool:bash"
        assert rule.permission == PermissionLevel.DENY
        assert rule.priority == 100

    def test_allow_returns_none(self):
        """Test ALLOW returns None (no rule created)."""
        rule = create_rule_from_choice(ConfirmationChoice.ALLOW, "bash", {})
        assert rule is None

    def test_deny_returns_none(self):
        """Test DENY returns None (no rule created)."""
        rule = create_rule_from_choice(ConfirmationChoice.DENY, "bash", {})
        assert rule is None

    def test_timeout_returns_none(self):
        """Test TIMEOUT returns None (no rule created)."""
        rule = create_rule_from_choice(ConfirmationChoice.TIMEOUT, "bash", {})
        assert rule is None

    def test_rule_description_contains_tool_name(self):
        """Test that rule description contains tool name."""
        rule = create_rule_from_choice(
            ConfirmationChoice.ALLOW_ALWAYS, "custom_tool", {}
        )

        assert isinstance(rule, PermissionRule)
        assert "custom_tool" in rule.description

    def test_arguments_not_used_in_pattern(self):
        """Test that arguments are not included in pattern."""
        rule = create_rule_from_choice(
            ConfirmationChoice.ALLOW_ALWAYS,
            "bash",
            {"command": "ls", "timeout": 30},
        )

        assert isinstance(rule, PermissionRule)
        assert rule.pattern == "tool:bash"
        # Arguments are not included in the simple pattern
        assert "arg:" not in rule.pattern


class TestPermissionPromptIntegration:
    """Integration tests for permission prompt."""

    def test_full_confirmation_flow(self):
        """Test complete confirmation flow."""
        inputs = iter(["a", "A", "d", "D", "", "invalid"])
        mock_input = MagicMock(side_effect=lambda p: next(inputs))
        mock_output = MagicMock()

        prompt = PermissionPrompt(
            input_handler=mock_input, output_handler=mock_output
        )
        request = ConfirmationRequest(tool_name="bash", arguments={})

        # Test each input type
        assert prompt.confirm(request) == ConfirmationChoice.ALLOW
        assert prompt.confirm(request) == ConfirmationChoice.ALLOW_ALWAYS
        assert prompt.confirm(request) == ConfirmationChoice.DENY
        assert prompt.confirm(request) == ConfirmationChoice.DENY_ALWAYS
        assert prompt.confirm(request) == ConfirmationChoice.DENY  # empty
        assert prompt.confirm(request) == ConfirmationChoice.DENY  # invalid
