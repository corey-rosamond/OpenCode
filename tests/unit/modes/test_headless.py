"""Tests for Headless mode."""

import io
import json
import tempfile
import time
from pathlib import Path

import pytest

from code_forge.modes.base import ModeContext, ModeName
from code_forge.modes.headless import (
    HeadlessConfig,
    HeadlessMode,
    HeadlessResult,
    OutputFormat,
    create_headless_config_from_args,
)


class TestOutputFormat:
    """Tests for OutputFormat enum."""

    def test_text_value(self) -> None:
        """Test TEXT format value."""
        assert OutputFormat.TEXT.value == "text"

    def test_json_value(self) -> None:
        """Test JSON format value."""
        assert OutputFormat.JSON.value == "json"


class TestHeadlessConfig:
    """Tests for HeadlessConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = HeadlessConfig()
        assert config.input_file is None
        assert config.output_file is None
        assert config.output_format == OutputFormat.TEXT
        assert config.timeout == 300
        assert config.auto_approve_safe is True
        assert config.fail_on_unsafe is True
        assert config.exit_on_complete is True

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = HeadlessConfig(
            input_file="input.txt",
            output_file="output.json",
            output_format=OutputFormat.JSON,
            timeout=60,
            auto_approve_safe=False,
            fail_on_unsafe=False,
            exit_on_complete=False,
        )
        assert config.input_file == "input.txt"
        assert config.output_file == "output.json"
        assert config.output_format == OutputFormat.JSON
        assert config.timeout == 60
        assert config.auto_approve_safe is False


class TestHeadlessResult:
    """Tests for HeadlessResult dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic result creation."""
        result = HeadlessResult(
            success=True,
            message="Completed successfully",
        )
        assert result.success is True
        assert result.message == "Completed successfully"
        assert result.output == ""
        assert result.error is None
        assert result.exit_code == 0
        assert result.execution_time == 0.0
        assert result.details == {}

    def test_failure_result(self) -> None:
        """Test failure result."""
        result = HeadlessResult(
            success=False,
            message="Failed",
            error="Something went wrong",
            exit_code=1,
        )
        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.exit_code == 1

    def test_with_output(self) -> None:
        """Test result with output."""
        result = HeadlessResult(
            success=True,
            message="Done",
            output="The result is 42",
        )
        assert result.output == "The result is 42"

    def test_with_details(self) -> None:
        """Test result with details."""
        result = HeadlessResult(
            success=True,
            message="Done",
            details={"files_modified": 3, "tests_run": 10},
        )
        assert result.details["files_modified"] == 3
        assert result.details["tests_run"] == 10

    def test_to_json(self) -> None:
        """Test JSON conversion."""
        result = HeadlessResult(
            success=True,
            message="Done",
            output="Output text",
            execution_time=1.5,
        )
        json_str = result.to_json()
        data = json.loads(json_str)

        assert data["status"] == "success"
        assert data["message"] == "Done"
        assert data["output"] == "Output text"
        assert data["execution_time"] == 1.5
        assert "timestamp" in data

    def test_to_json_failure(self) -> None:
        """Test JSON conversion for failure."""
        result = HeadlessResult(
            success=False,
            message="Failed",
            error="Error message",
            exit_code=1,
        )
        json_str = result.to_json()
        data = json.loads(json_str)

        assert data["status"] == "failure"
        assert data["error"] == "Error message"
        assert data["exit_code"] == 1

    def test_to_text(self) -> None:
        """Test text conversion."""
        result = HeadlessResult(
            success=True,
            message="Done",
            output="Output text",
        )
        text = result.to_text()

        assert "Done" in text
        assert "Output text" in text

    def test_to_text_with_error(self) -> None:
        """Test text conversion with error."""
        result = HeadlessResult(
            success=False,
            message="Failed",
            error="Error message",
        )
        text = result.to_text()

        assert "Failed" in text
        assert "Error: Error message" in text

    def test_to_text_with_details(self) -> None:
        """Test text conversion with details."""
        result = HeadlessResult(
            success=True,
            message="Done",
            details={"key": "value"},
        )
        text = result.to_text()

        assert "Details:" in text
        assert "key: value" in text

    def test_to_dict(self) -> None:
        """Test dictionary conversion."""
        result = HeadlessResult(
            success=True,
            message="Done",
            output="Output",
            execution_time=1.0,
        )
        data = result.to_dict()

        assert data["success"] is True
        assert data["message"] == "Done"
        assert data["output"] == "Output"
        assert data["execution_time"] == 1.0

    def test_from_dict(self) -> None:
        """Test deserialization from dict."""
        data = {
            "success": True,
            "message": "Done",
            "output": "Output",
            "error": None,
            "exit_code": 0,
            "execution_time": 1.5,
            "details": {"key": "value"},
            "timestamp": "2025-01-01T12:00:00",
        }
        result = HeadlessResult.from_dict(data)

        assert result.success is True
        assert result.message == "Done"
        assert result.output == "Output"
        assert result.execution_time == 1.5
        assert result.details == {"key": "value"}

    def test_roundtrip(self) -> None:
        """Test serialization roundtrip."""
        original = HeadlessResult(
            success=True,
            message="Test",
            output="Output",
            execution_time=2.5,
            details={"test": "data"},
        )
        restored = HeadlessResult.from_dict(original.to_dict())

        assert restored.success == original.success
        assert restored.message == original.message
        assert restored.output == original.output
        assert restored.execution_time == original.execution_time


class TestHeadlessMode:
    """Tests for HeadlessMode class."""

    @pytest.fixture
    def mode(self) -> HeadlessMode:
        """Create headless mode for tests."""
        return HeadlessMode()

    @pytest.fixture
    def context(self) -> ModeContext:
        """Create test context."""
        return ModeContext(output=lambda m: None)

    def test_name(self, mode: HeadlessMode) -> None:
        """Test mode name."""
        assert mode.name == ModeName.HEADLESS

    def test_default_config(self, mode: HeadlessMode) -> None:
        """Test default configuration."""
        assert mode.config.name == ModeName.HEADLESS
        assert mode.config.description == "Non-interactive automation mode"
        assert "HEADLESS MODE" in mode.config.system_prompt_addition

    def test_default_headless_config(self, mode: HeadlessMode) -> None:
        """Test default headless config."""
        assert mode.headless_config.timeout == 300
        assert mode.headless_config.auto_approve_safe is True

    def test_custom_headless_config(self) -> None:
        """Test custom headless config."""
        config = HeadlessConfig(timeout=60, auto_approve_safe=False)
        mode = HeadlessMode(headless_config=config)
        assert mode.headless_config.timeout == 60
        assert mode.headless_config.auto_approve_safe is False

    def test_initial_state(self, mode: HeadlessMode) -> None:
        """Test initial state."""
        assert mode.is_active is False
        assert mode._start_time is None
        assert mode._input_stream is None
        assert mode._output_stream is None

    def test_activate_stdin_stdout(
        self, mode: HeadlessMode, context: ModeContext
    ) -> None:
        """Test activation with stdin/stdout."""
        mode.activate(context)

        assert mode.is_active is True
        assert isinstance(mode._start_time, float)
        assert mode._start_time > 0
        # Should use stdin/stdout - hasattr checks implicitly verify not None
        assert hasattr(mode._input_stream, 'read')
        assert hasattr(mode._output_stream, 'write')
        assert mode._owns_input_stream is False
        assert mode._owns_output_stream is False

        mode.deactivate(context)

    def test_activate_with_input_file(self, context: ModeContext) -> None:
        """Test activation with input file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test input")
            input_path = f.name

        try:
            config = HeadlessConfig(input_file=input_path)
            mode = HeadlessMode(headless_config=config)

            mode.activate(context)

            assert mode._owns_input_stream is True
            assert isinstance(mode._input_stream, io.IOBase)
            assert hasattr(mode._input_stream, 'read')

            mode.deactivate(context)
        finally:
            Path(input_path).unlink()

    def test_activate_input_file_not_found(self, context: ModeContext) -> None:
        """Test activation with non-existent input file."""
        config = HeadlessConfig(input_file="/nonexistent/file.txt")
        mode = HeadlessMode(headless_config=config)

        with pytest.raises(FileNotFoundError):
            mode.activate(context)

    def test_activate_with_output_file(self, context: ModeContext) -> None:
        """Test activation with output file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.txt"
            config = HeadlessConfig(output_file=str(output_path))
            mode = HeadlessMode(headless_config=config)

            mode.activate(context)

            assert mode._owns_output_stream is True
            assert isinstance(mode._output_stream, io.IOBase)
            assert hasattr(mode._output_stream, 'write')

            mode.deactivate(context)

    def test_deactivate_closes_streams(self, context: ModeContext) -> None:
        """Test deactivation closes owned streams."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test")
            input_path = f.name

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.txt"
            config = HeadlessConfig(
                input_file=input_path,
                output_file=str(output_path),
            )
            mode = HeadlessMode(headless_config=config)

            mode.activate(context)
            mode.deactivate(context)

            assert mode._input_stream is None
            assert mode._output_stream is None
            assert mode._start_time is None

        Path(input_path).unlink()

    def test_read_input(self, context: ModeContext) -> None:
        """Test reading input from file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test input content")
            input_path = f.name

        try:
            config = HeadlessConfig(input_file=input_path)
            mode = HeadlessMode(headless_config=config)

            mode.activate(context)
            content = mode.read_input()

            assert content == "Test input content"

            mode.deactivate(context)
        finally:
            Path(input_path).unlink()

    def test_write_output_text(self, context: ModeContext) -> None:
        """Test writing text output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.txt"
            config = HeadlessConfig(
                output_file=str(output_path),
                output_format=OutputFormat.TEXT,
            )
            mode = HeadlessMode(headless_config=config)

            mode.activate(context)

            result = HeadlessResult(success=True, message="Done", output="Result")
            mode.write_output(result)

            mode.deactivate(context)

            content = output_path.read_text()
            assert "Done" in content
            assert "Result" in content

    def test_write_output_json(self, context: ModeContext) -> None:
        """Test writing JSON output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.json"
            config = HeadlessConfig(
                output_file=str(output_path),
                output_format=OutputFormat.JSON,
            )
            mode = HeadlessMode(headless_config=config)

            mode.activate(context)

            result = HeadlessResult(success=True, message="Done")
            mode.write_output(result)

            mode.deactivate(context)

            content = output_path.read_text()
            data = json.loads(content.strip())
            assert data["status"] == "success"
            assert data["message"] == "Done"

    def test_handle_permission_safe_auto_approve(
        self, mode: HeadlessMode
    ) -> None:
        """Test safe permission with auto-approve."""
        mode.headless_config.auto_approve_safe = True
        result = mode.handle_permission_request("read file", is_safe=True)
        assert result is True

    def test_handle_permission_safe_no_auto_approve(
        self, mode: HeadlessMode
    ) -> None:
        """Test safe permission without auto-approve."""
        mode.headless_config.auto_approve_safe = False
        result = mode.handle_permission_request("read file", is_safe=True)
        assert result is False

    def test_handle_permission_unsafe_fail(self, mode: HeadlessMode) -> None:
        """Test unsafe permission with fail_on_unsafe."""
        mode.headless_config.fail_on_unsafe = True
        result = mode.handle_permission_request("delete all", is_safe=False)
        assert result is False

    def test_handle_permission_unsafe_allow(self, mode: HeadlessMode) -> None:
        """Test unsafe permission without fail_on_unsafe."""
        mode.headless_config.fail_on_unsafe = False
        mode.headless_config.auto_approve_safe = False
        result = mode.handle_permission_request("delete all", is_safe=False)
        # Default to deny even if not explicitly failing
        assert result is False

    def test_create_result_success(
        self, mode: HeadlessMode, context: ModeContext
    ) -> None:
        """Test creating success result."""
        mode.activate(context)
        time.sleep(0.01)  # Small delay for measurable time

        result = mode.create_result(
            success=True,
            message="Done",
            output="Result",
        )

        assert result.success is True
        assert result.message == "Done"
        assert result.output == "Result"
        assert result.exit_code == 0
        assert result.execution_time > 0

        mode.deactivate(context)

    def test_create_result_failure(
        self, mode: HeadlessMode, context: ModeContext
    ) -> None:
        """Test creating failure result."""
        mode.activate(context)

        result = mode.create_result(
            success=False,
            message="Failed",
            error="Error message",
        )

        assert result.success is False
        assert result.message == "Failed"
        assert result.error == "Error message"
        assert result.exit_code == 1

        mode.deactivate(context)

    def test_create_result_with_details(
        self, mode: HeadlessMode, context: ModeContext
    ) -> None:
        """Test creating result with details."""
        mode.activate(context)

        result = mode.create_result(
            success=True,
            message="Done",
            details={"key": "value"},
        )

        assert result.details == {"key": "value"}

        mode.deactivate(context)

    def test_modify_response_text(
        self, mode: HeadlessMode, context: ModeContext
    ) -> None:
        """Test response modification in text mode."""
        mode.headless_config.output_format = OutputFormat.TEXT
        mode.activate(context)

        response = "Plain response"
        result = mode.modify_response(response)

        assert result == response

        mode.deactivate(context)

    def test_modify_response_json(
        self, mode: HeadlessMode, context: ModeContext
    ) -> None:
        """Test response modification in JSON mode."""
        mode.headless_config.output_format = OutputFormat.JSON
        mode.activate(context)

        response = "Plain response"
        result = mode.modify_response(response)

        # Should be JSON
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["output"] == response

        mode.deactivate(context)

    def test_check_timeout_not_expired(
        self, mode: HeadlessMode, context: ModeContext
    ) -> None:
        """Test timeout not expired."""
        mode.headless_config.timeout = 300
        mode.activate(context)

        assert mode.check_timeout() is False

        mode.deactivate(context)

    def test_check_timeout_expired(
        self, mode: HeadlessMode, context: ModeContext
    ) -> None:
        """Test timeout expired."""
        mode.headless_config.timeout = 0  # Immediate timeout
        mode.activate(context)
        time.sleep(0.01)

        assert mode.check_timeout() is True

        mode.deactivate(context)

    def test_check_timeout_not_activated(self, mode: HeadlessMode) -> None:
        """Test timeout when not activated."""
        assert mode.check_timeout() is False


class TestCreateHeadlessConfigFromArgs:
    """Tests for create_headless_config_from_args function."""

    def test_defaults(self) -> None:
        """Test default config from no args."""
        config = create_headless_config_from_args()
        assert config.input_file is None
        assert config.output_file is None
        assert config.output_format == OutputFormat.TEXT
        assert config.timeout == 300

    def test_with_input_file(self) -> None:
        """Test config with input file."""
        config = create_headless_config_from_args(input_file="input.txt")
        assert config.input_file == "input.txt"

    def test_with_output_file(self) -> None:
        """Test config with output file."""
        config = create_headless_config_from_args(output_file="output.txt")
        assert config.output_file == "output.txt"

    def test_with_json_output(self) -> None:
        """Test config with JSON output."""
        config = create_headless_config_from_args(json_output=True)
        assert config.output_format == OutputFormat.JSON

    def test_with_timeout(self) -> None:
        """Test config with custom timeout."""
        config = create_headless_config_from_args(timeout=60)
        assert config.timeout == 60

    def test_all_args(self) -> None:
        """Test config with all args."""
        config = create_headless_config_from_args(
            input_file="in.txt",
            output_file="out.json",
            json_output=True,
            timeout=120,
        )
        assert config.input_file == "in.txt"
        assert config.output_file == "out.json"
        assert config.output_format == OutputFormat.JSON
        assert config.timeout == 120
