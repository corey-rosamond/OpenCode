"""Tests for MCP protocol types."""

from __future__ import annotations

import json
import uuid

import pytest

from code_forge.mcp.protocol import (
    MCPCapabilities,
    MCPError,
    MCPNotification,
    MCPPrompt,
    MCPPromptArgument,
    MCPPromptMessage,
    MCPRequest,
    MCPResource,
    MCPResourceTemplate,
    MCPResponse,
    MCPServerInfo,
    MCPTool,
    parse_json_message,
    parse_message,
)


class TestMCPError:
    """Tests for MCPError."""

    def test_creation(self) -> None:
        """Test basic creation."""
        error = MCPError(code=-32600, message="Invalid request")
        assert error.code == -32600
        assert error.message == "Invalid request"
        assert error.data is None

    def test_creation_with_data(self) -> None:
        """Test creation with data."""
        error = MCPError(code=-32602, message="Invalid params", data={"field": "name"})
        assert error.code == -32602
        assert error.message == "Invalid params"
        assert error.data == {"field": "name"}

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        error = MCPError(code=-32700, message="Parse error")
        d = error.to_dict()
        assert d == {"code": -32700, "message": "Parse error"}

    def test_to_dict_with_data(self) -> None:
        """Test conversion to dictionary with data."""
        error = MCPError(code=-32603, message="Internal error", data="details")
        d = error.to_dict()
        assert d == {"code": -32603, "message": "Internal error", "data": "details"}

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        d = {"code": -32601, "message": "Method not found"}
        error = MCPError.from_dict(d)
        assert error.code == -32601
        assert error.message == "Method not found"
        assert error.data is None

    def test_from_dict_with_data(self) -> None:
        """Test creation from dictionary with data."""
        d = {"code": -32602, "message": "Invalid params", "data": {"param": "x"}}
        error = MCPError.from_dict(d)
        assert error.code == -32602
        assert error.message == "Invalid params"
        assert error.data == {"param": "x"}

    def test_factory_methods(self) -> None:
        """Test factory methods for standard errors."""
        parse_err = MCPError.parse_error()
        assert parse_err.code == -32700

        invalid_req = MCPError.invalid_request()
        assert invalid_req.code == -32600

        method_not_found = MCPError.method_not_found()
        assert method_not_found.code == -32601

        invalid_params = MCPError.invalid_params()
        assert invalid_params.code == -32602

        internal = MCPError.internal_error()
        assert internal.code == -32603

    def test_factory_methods_with_custom_message(self) -> None:
        """Test factory methods with custom messages."""
        err = MCPError.parse_error("Custom parse error")
        assert err.message == "Custom parse error"


class TestMCPRequest:
    """Tests for MCPRequest."""

    def test_creation(self) -> None:
        """Test basic creation."""
        request = MCPRequest(method="tools/list")
        assert request.method == "tools/list"
        assert request.params is None
        assert isinstance(request.id, str) and len(request.id) > 0

    def test_creation_with_params(self) -> None:
        """Test creation with parameters."""
        request = MCPRequest(method="tools/call", params={"name": "test"})
        assert request.method == "tools/call"
        assert request.params == {"name": "test"}

    def test_creation_with_custom_id(self) -> None:
        """Test creation with custom ID."""
        request = MCPRequest(method="test", id="custom-id")
        assert request.id == "custom-id"

    def test_auto_id_generation(self) -> None:
        """Test automatic ID generation."""
        request1 = MCPRequest(method="test")
        request2 = MCPRequest(method="test")
        assert request1.id != request2.id
        # Should be valid UUIDs
        uuid.UUID(str(request1.id))
        uuid.UUID(str(request2.id))

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        request = MCPRequest(method="tools/list", id="123")
        d = request.to_dict()
        assert d["jsonrpc"] == "2.0"
        assert d["method"] == "tools/list"
        assert d["id"] == "123"
        assert "params" not in d

    def test_to_dict_with_params(self) -> None:
        """Test conversion to dictionary with params."""
        request = MCPRequest(method="tools/call", params={"name": "test"}, id="456")
        d = request.to_dict()
        assert d["params"] == {"name": "test"}

    def test_to_json(self) -> None:
        """Test conversion to JSON string."""
        request = MCPRequest(method="test", id="789")
        json_str = request.to_json()
        parsed = json.loads(json_str)
        assert parsed["jsonrpc"] == "2.0"
        assert parsed["method"] == "test"
        assert parsed["id"] == "789"

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        d = {"method": "test", "params": {"key": "value"}, "id": "abc"}
        request = MCPRequest.from_dict(d)
        assert request.method == "test"
        assert request.params == {"key": "value"}
        assert request.id == "abc"


class TestMCPResponse:
    """Tests for MCPResponse."""

    def test_success_response(self) -> None:
        """Test successful response."""
        response = MCPResponse(id="123", result={"tools": []})
        assert response.id == "123"
        assert response.result == {"tools": []}
        assert response.error is None
        assert not response.is_error

    def test_error_response(self) -> None:
        """Test error response."""
        error = MCPError(code=-32601, message="Method not found")
        response = MCPResponse(id="456", error=error)
        assert response.id == "456"
        assert response.result is None
        assert isinstance(response.error, MCPError)
        assert response.is_error

    def test_to_dict_success(self) -> None:
        """Test conversion to dictionary for success."""
        response = MCPResponse(id="123", result={"data": "test"})
        d = response.to_dict()
        assert d["jsonrpc"] == "2.0"
        assert d["id"] == "123"
        assert d["result"] == {"data": "test"}
        assert "error" not in d

    def test_to_dict_error(self) -> None:
        """Test conversion to dictionary for error."""
        error = MCPError(code=-32700, message="Parse error")
        response = MCPResponse(id="789", error=error)
        d = response.to_dict()
        assert d["jsonrpc"] == "2.0"
        assert d["id"] == "789"
        assert d["error"] == {"code": -32700, "message": "Parse error"}
        assert "result" not in d

    def test_to_json(self) -> None:
        """Test conversion to JSON string."""
        response = MCPResponse(id="test", result="ok")
        json_str = response.to_json()
        parsed = json.loads(json_str)
        assert parsed["result"] == "ok"

    def test_from_dict_success(self) -> None:
        """Test creation from dictionary for success."""
        d = {"jsonrpc": "2.0", "id": "abc", "result": {"tools": []}}
        response = MCPResponse.from_dict(d)
        assert response.id == "abc"
        assert response.result == {"tools": []}
        assert response.error is None

    def test_from_dict_error(self) -> None:
        """Test creation from dictionary for error."""
        d = {
            "jsonrpc": "2.0",
            "id": "def",
            "error": {"code": -32600, "message": "Invalid request"},
        }
        response = MCPResponse.from_dict(d)
        assert response.id == "def"
        assert isinstance(response.error, MCPError)
        assert response.error.code == -32600

    def test_factory_methods(self) -> None:
        """Test factory methods."""
        success = MCPResponse.success("id1", {"result": "data"})
        assert not success.is_error
        assert success.result == {"result": "data"}

        error = MCPError(code=-1, message="fail")
        failure = MCPResponse.failure("id2", error)
        assert failure.is_error
        assert isinstance(failure.error, MCPError)


class TestMCPNotification:
    """Tests for MCPNotification."""

    def test_creation(self) -> None:
        """Test basic creation."""
        notif = MCPNotification(method="notifications/initialized")
        assert notif.method == "notifications/initialized"
        assert notif.params is None

    def test_creation_with_params(self) -> None:
        """Test creation with parameters."""
        notif = MCPNotification(method="notifications/progress", params={"percent": 50})
        assert notif.method == "notifications/progress"
        assert notif.params == {"percent": 50}

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        notif = MCPNotification(method="test")
        d = notif.to_dict()
        assert d["jsonrpc"] == "2.0"
        assert d["method"] == "test"
        assert "id" not in d
        assert "params" not in d

    def test_to_dict_with_params(self) -> None:
        """Test conversion to dictionary with params."""
        notif = MCPNotification(method="test", params={"key": "value"})
        d = notif.to_dict()
        assert d["params"] == {"key": "value"}

    def test_to_json(self) -> None:
        """Test conversion to JSON string."""
        notif = MCPNotification(method="test")
        json_str = notif.to_json()
        parsed = json.loads(json_str)
        assert "id" not in parsed

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        d = {"method": "test", "params": {"data": 123}}
        notif = MCPNotification.from_dict(d)
        assert notif.method == "test"
        assert notif.params == {"data": 123}


class TestMCPTool:
    """Tests for MCPTool."""

    def test_creation(self) -> None:
        """Test basic creation."""
        tool = MCPTool(
            name="read_file",
            description="Read a file",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}}},
        )
        assert tool.name == "read_file"
        assert tool.description == "Read a file"
        assert "properties" in tool.input_schema

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        d = {
            "name": "write_file",
            "description": "Write to a file",
            "inputSchema": {"type": "object"},
        }
        tool = MCPTool.from_dict(d)
        assert tool.name == "write_file"
        assert tool.description == "Write to a file"
        assert tool.input_schema == {"type": "object"}

    def test_from_dict_defaults(self) -> None:
        """Test creation from dictionary with defaults."""
        d = {"name": "test"}
        tool = MCPTool.from_dict(d)
        assert tool.name == "test"
        assert tool.description == ""
        assert tool.input_schema == {}

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        tool = MCPTool(name="test", description="desc", input_schema={"type": "object"})
        d = tool.to_dict()
        assert d["name"] == "test"
        assert d["description"] == "desc"
        assert d["inputSchema"] == {"type": "object"}


class TestMCPResource:
    """Tests for MCPResource."""

    def test_creation(self) -> None:
        """Test basic creation."""
        resource = MCPResource(uri="file:///tmp/test.txt", name="test.txt")
        assert resource.uri == "file:///tmp/test.txt"
        assert resource.name == "test.txt"
        assert resource.description is None
        assert resource.mime_type is None

    def test_creation_full(self) -> None:
        """Test creation with all fields."""
        resource = MCPResource(
            uri="file:///tmp/test.txt",
            name="test.txt",
            description="A test file",
            mime_type="text/plain",
        )
        assert resource.description == "A test file"
        assert resource.mime_type == "text/plain"

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        d = {
            "uri": "http://example.com/data",
            "name": "data",
            "description": "Some data",
            "mimeType": "application/json",
        }
        resource = MCPResource.from_dict(d)
        assert resource.uri == "http://example.com/data"
        assert resource.name == "data"
        assert resource.description == "Some data"
        assert resource.mime_type == "application/json"

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        resource = MCPResource(
            uri="file:///test", name="test", description="desc", mime_type="text/plain"
        )
        d = resource.to_dict()
        assert d["uri"] == "file:///test"
        assert d["name"] == "test"
        assert d["description"] == "desc"
        assert d["mimeType"] == "text/plain"

    def test_to_dict_minimal(self) -> None:
        """Test conversion to dictionary with minimal fields."""
        resource = MCPResource(uri="file:///test", name="test")
        d = resource.to_dict()
        assert "description" not in d
        assert "mimeType" not in d


class TestMCPResourceTemplate:
    """Tests for MCPResourceTemplate."""

    def test_creation(self) -> None:
        """Test basic creation."""
        template = MCPResourceTemplate(
            uri_template="file:///{path}", name="File template"
        )
        assert template.uri_template == "file:///{path}"
        assert template.name == "File template"

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        d = {
            "uriTemplate": "db:///{database}/{table}",
            "name": "Database table",
            "description": "Access database tables",
            "mimeType": "application/json",
        }
        template = MCPResourceTemplate.from_dict(d)
        assert template.uri_template == "db:///{database}/{table}"
        assert template.name == "Database table"
        assert template.description == "Access database tables"
        assert template.mime_type == "application/json"

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        template = MCPResourceTemplate(
            uri_template="test:///{id}",
            name="Test",
            description="desc",
            mime_type="text/plain",
        )
        d = template.to_dict()
        assert d["uriTemplate"] == "test:///{id}"
        assert d["name"] == "Test"
        assert d["description"] == "desc"
        assert d["mimeType"] == "text/plain"


class TestMCPPromptArgument:
    """Tests for MCPPromptArgument."""

    def test_creation(self) -> None:
        """Test basic creation."""
        arg = MCPPromptArgument(name="topic")
        assert arg.name == "topic"
        assert arg.description is None
        assert arg.required is False

    def test_creation_full(self) -> None:
        """Test creation with all fields."""
        arg = MCPPromptArgument(
            name="topic", description="The topic to discuss", required=True
        )
        assert arg.name == "topic"
        assert arg.description == "The topic to discuss"
        assert arg.required is True

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        d = {"name": "length", "description": "Output length", "required": True}
        arg = MCPPromptArgument.from_dict(d)
        assert arg.name == "length"
        assert arg.description == "Output length"
        assert arg.required is True

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        arg = MCPPromptArgument(
            name="test", description="Test arg", required=True
        )
        d = arg.to_dict()
        assert d["name"] == "test"
        assert d["description"] == "Test arg"
        assert d["required"] is True

    def test_to_dict_minimal(self) -> None:
        """Test conversion to dictionary with minimal fields."""
        arg = MCPPromptArgument(name="test")
        d = arg.to_dict()
        assert d == {"name": "test"}


class TestMCPPrompt:
    """Tests for MCPPrompt."""

    def test_creation(self) -> None:
        """Test basic creation."""
        prompt = MCPPrompt(name="summarize")
        assert prompt.name == "summarize"
        assert prompt.description is None
        assert prompt.arguments is None

    def test_creation_full(self) -> None:
        """Test creation with all fields."""
        args = [MCPPromptArgument(name="text", required=True)]
        prompt = MCPPrompt(
            name="summarize", description="Summarize text", arguments=args
        )
        assert prompt.name == "summarize"
        assert prompt.description == "Summarize text"
        assert isinstance(prompt.arguments, list)
        assert len(prompt.arguments) == 1

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        d = {
            "name": "translate",
            "description": "Translate text",
            "arguments": [
                {"name": "text", "required": True},
                {"name": "target_lang", "description": "Target language"},
            ],
        }
        prompt = MCPPrompt.from_dict(d)
        assert prompt.name == "translate"
        assert prompt.description == "Translate text"
        assert isinstance(prompt.arguments, list)
        assert len(prompt.arguments) == 2
        assert prompt.arguments[0].name == "text"
        assert prompt.arguments[1].name == "target_lang"

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        args = [MCPPromptArgument(name="input", required=True)]
        prompt = MCPPrompt(name="test", description="Test prompt", arguments=args)
        d = prompt.to_dict()
        assert d["name"] == "test"
        assert d["description"] == "Test prompt"
        assert len(d["arguments"]) == 1


class TestMCPPromptMessage:
    """Tests for MCPPromptMessage."""

    def test_creation(self) -> None:
        """Test basic creation."""
        msg = MCPPromptMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_creation_dict_content(self) -> None:
        """Test creation with dict content."""
        msg = MCPPromptMessage(
            role="assistant", content={"type": "text", "text": "Hi"}
        )
        assert msg.role == "assistant"
        assert msg.content == {"type": "text", "text": "Hi"}

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        d = {"role": "system", "content": "You are helpful"}
        msg = MCPPromptMessage.from_dict(d)
        assert msg.role == "system"
        assert msg.content == "You are helpful"

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        msg = MCPPromptMessage(role="user", content="Test")
        d = msg.to_dict()
        assert d == {"role": "user", "content": "Test"}


class TestMCPCapabilities:
    """Tests for MCPCapabilities."""

    def test_defaults(self) -> None:
        """Test default values."""
        caps = MCPCapabilities()
        assert caps.tools is False
        assert caps.resources is False
        assert caps.prompts is False
        assert caps.logging is False

    def test_from_dict_empty(self) -> None:
        """Test creation from empty dictionary."""
        caps = MCPCapabilities.from_dict({})
        assert caps.tools is False
        assert caps.resources is False

    def test_from_dict_with_capabilities(self) -> None:
        """Test creation from dictionary with capabilities."""
        d = {"capabilities": {"tools": {}, "resources": {}, "prompts": {}}}
        caps = MCPCapabilities.from_dict(d)
        assert caps.tools is True
        assert caps.resources is True
        assert caps.prompts is True
        assert caps.logging is False

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        caps = MCPCapabilities(tools=True, resources=True, prompts=False, logging=True)
        d = caps.to_dict()
        assert "tools" in d["capabilities"]
        assert "resources" in d["capabilities"]
        assert "prompts" not in d["capabilities"]
        assert "logging" in d["capabilities"]


class TestMCPServerInfo:
    """Tests for MCPServerInfo."""

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        d = {
            "serverInfo": {"name": "test-server", "version": "1.2.3"},
            "capabilities": {"tools": {}, "resources": {}},
        }
        info = MCPServerInfo.from_dict(d)
        assert info.name == "test-server"
        assert info.version == "1.2.3"
        assert info.capabilities.tools is True
        assert info.capabilities.resources is True

    def test_from_dict_defaults(self) -> None:
        """Test creation from dictionary with defaults."""
        d = {}
        info = MCPServerInfo.from_dict(d)
        assert info.name == "unknown"
        assert info.version == "0.0.0"
        assert info.capabilities.tools is False

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        caps = MCPCapabilities(tools=True)
        info = MCPServerInfo(name="my-server", version="2.0.0", capabilities=caps)
        d = info.to_dict()
        assert d["serverInfo"]["name"] == "my-server"
        assert d["serverInfo"]["version"] == "2.0.0"
        assert "tools" in d["capabilities"]


class TestParseMessage:
    """Tests for parse_message function."""

    def test_parse_request(self) -> None:
        """Test parsing a request."""
        data = {"jsonrpc": "2.0", "method": "test", "id": "123", "params": {"key": 1}}
        msg = parse_message(data)
        assert isinstance(msg, MCPRequest)
        assert msg.method == "test"
        assert msg.id == "123"
        assert msg.params == {"key": 1}

    def test_parse_notification(self) -> None:
        """Test parsing a notification."""
        data = {"jsonrpc": "2.0", "method": "notify", "params": {}}
        msg = parse_message(data)
        assert isinstance(msg, MCPNotification)
        assert msg.method == "notify"

    def test_parse_response_success(self) -> None:
        """Test parsing a success response."""
        data = {"jsonrpc": "2.0", "id": "456", "result": {"data": "test"}}
        msg = parse_message(data)
        assert isinstance(msg, MCPResponse)
        assert msg.id == "456"
        assert msg.result == {"data": "test"}
        assert not msg.is_error

    def test_parse_response_error(self) -> None:
        """Test parsing an error response."""
        data = {
            "jsonrpc": "2.0",
            "id": "789",
            "error": {"code": -32600, "message": "Invalid"},
        }
        msg = parse_message(data)
        assert isinstance(msg, MCPResponse)
        assert msg.is_error
        assert isinstance(msg.error, MCPError)
        assert msg.error.code == -32600

    def test_parse_invalid_message(self) -> None:
        """Test parsing an invalid message."""
        data = {"jsonrpc": "2.0"}
        with pytest.raises(ValueError, match="Invalid JSON-RPC message"):
            parse_message(data)


class TestParseJsonMessage:
    """Tests for parse_json_message function."""

    def test_parse_valid_json(self) -> None:
        """Test parsing valid JSON."""
        json_str = '{"jsonrpc": "2.0", "method": "test", "id": "1"}'
        msg = parse_json_message(json_str)
        assert isinstance(msg, MCPRequest)
        assert msg.method == "test"

    def test_parse_invalid_json(self) -> None:
        """Test parsing invalid JSON."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            parse_json_message("not valid json")

    def test_parse_invalid_message(self) -> None:
        """Test parsing valid JSON but invalid message."""
        with pytest.raises(ValueError, match="Invalid JSON-RPC message"):
            parse_json_message('{"jsonrpc": "2.0"}')
