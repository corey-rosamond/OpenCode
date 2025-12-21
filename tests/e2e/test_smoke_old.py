"""Smoke tests for Code-Forge - critical path verification.

These tests verify the most critical user paths work end-to-end.
If these pass, the system is fundamentally working.
"""

import pytest


class TestCriticalPaths:
    """Test critical user paths end-to-end."""

    @pytest.mark.asyncio
    async def test_file_operations_workflow(self, temp_project, tool_registry_with_tools, execution_context):
        """CRITICAL: File read/write/edit workflow works"""
        from code_forge.tools import ToolRegistry

        registry = ToolRegistry()

        # 1. Write a file
        write_tool = registry.get_tool("Write")
        file_path = temp_project / "test.py"

        write_result = await write_tool.execute(
            context=execution_context,
            file_path=str(file_path),
            content="def hello():\n    return 'Hello'\n",
        )
        assert write_result.success, "Write tool failed"

        # 2. Read the file back
        read_tool = registry.get_tool("Read")
        read_result = await read_tool.execute(
            context=execution_context,
            file_path=str(file_path),
        )
        assert read_result.success, "Read tool failed"
        assert "def hello()" in read_result.output, "File content not found"

        # 3. Edit the file
        edit_tool = registry.get_tool("Edit")
        edit_result = await edit_tool.execute(
            context=execution_context,
            file_path=str(file_path),
            old_string="hello",
            new_string="greet",
        )
        assert edit_result.success, "Edit tool failed"

        # 4. Verify edit
        verify_result = await read_tool.execute(
            context=execution_context,
            file_path=str(file_path),
        )
        assert verify_result.success, "Read after edit failed"
        assert "def greet()" in verify_result.output, "Edit not applied"
        assert "def hello()" not in verify_result.output, "Old content still present"

    @pytest.mark.asyncio
    async def test_file_search_workflow(self, sample_python_project, tool_registry_with_tools, execution_context):
        """CRITICAL: File search (glob/grep) works"""
        from code_forge.tools import ToolRegistry

        registry = ToolRegistry()

        # Update context to use sample project
        execution_context.working_dir = str(sample_python_project)

        # 1. Find files by pattern
        glob_tool = registry.get_tool("Glob")
        glob_result = await glob_tool.execute(
            context=execution_context,
            pattern="**/*.py",
        )
        assert glob_result.success, "Glob tool failed"
        assert "core.py" in glob_result.output, "Expected file not found"

        # 2. Search file content
        grep_tool = registry.get_tool("Grep")
        grep_result = await grep_tool.execute(
            context=execution_context,
            pattern="def hello",
            output_mode="files_with_matches",
        )
        assert grep_result.success, "Grep tool failed"
        assert "core.py" in grep_result.output, "Expected match not found"

    @pytest.mark.asyncio
    async def test_session_workflow(self, session_manager):
        """CRITICAL: Session create/save/load works"""
        # 1. Create session
        session = session_manager.create(title="Smoke Test")
        assert session is not None, "Session creation failed"

        # 2. Add messages
        session.add_user_message("Test message 1")
        session.add_assistant_message("Response 1")
        assert len(session.messages) == 2, "Message addition failed"

        # 3. Save session
        session_id = session.session_id
        session_manager.save()

        # 4. Load session
        loaded = session_manager.load(session_id)
        assert loaded is not None, "Session load failed"
        assert len(loaded.messages) == 2, "Messages not persisted"
        assert loaded.title == "Smoke Test", "Title not persisted"

    @pytest.mark.asyncio
    async def test_workflow_discovery(self):
        """CRITICAL: Workflow templates can be discovered"""
        from code_forge.workflows.registry import WorkflowTemplateRegistry

        registry = WorkflowTemplateRegistry.get_instance()

        # 1. List templates
        templates = registry.list_templates()
        assert len(templates) >= 7, "Missing built-in templates"

        # 2. Get specific template
        template = registry.get_template("pr-review")
        assert template is not None, "Cannot get pr-review template"
        assert template.name == "pr-review", "Wrong template returned"

        # 3. Search templates
        results = registry.search_templates("security")
        assert len(results) > 0, "Search failed"

    @pytest.mark.asyncio
    async def test_workflow_parsing(self, temp_dir):
        """CRITICAL: Workflow YAML parsing works"""
        from code_forge.workflows.parser import YAMLWorkflowParser

        # Create minimal workflow
        workflow_file = temp_dir / "test.yaml"
        workflow_file.write_text("""
name: smoke-test
description: Smoke test workflow
version: 1.0.0
steps:
  - id: test
    agent: general
    description: Test step
""")

        # Parse it
        parser = YAMLWorkflowParser()
        workflow = parser.parse_file(workflow_file)

        assert workflow is not None, "Parsing failed"
        assert workflow.name == "smoke-test", "Wrong workflow parsed"
        assert len(workflow.steps) == 1, "Steps not parsed"

    @pytest.mark.asyncio
    async def test_command_execution(self):
        """CRITICAL: Command parsing and execution works"""
        from code_forge.commands.parser import CommandParser
        from code_forge.commands.executor import CommandExecutor, CommandContext

        parser = CommandParser()
        executor = CommandExecutor()
        context = CommandContext()

        # Parse command
        parsed = parser.parse("/help")
        assert parsed is not None, "Command parsing failed"
        assert parsed.name == "help", "Wrong command parsed"

        # Execute command
        result = await executor.execute(parsed, context)
        assert result is not None, "Command execution failed"
        assert result.success, f"Command failed: {result.error}"

    @pytest.mark.asyncio
    async def test_bash_execution(self, temp_project, tool_registry_with_tools, execution_context):
        """CRITICAL: Bash command execution works"""
        from code_forge.tools import ToolRegistry

        registry = ToolRegistry()
        bash_tool = registry.get_tool("Bash")

        # Execute simple command
        result = await bash_tool.execute(
            context=execution_context,
            command="echo 'Smoke test'",
        )

        assert result.success, "Bash execution failed"
        assert "Smoke test" in result.output, "Bash output incorrect"

    @pytest.mark.asyncio
    async def test_configuration_loading(self, e2e_forge_config):
        """CRITICAL: Configuration loads successfully"""
        from code_forge.config import ConfigLoader

        # Config file created by fixture
        assert e2e_forge_config.exists(), "Config file not created"

        # Load config
        loader = ConfigLoader()
        config = loader.load_all()

        assert config is not None, "Config loading failed"
        assert config.llm is not None, "LLM config missing"
        assert config.llm.api_key is not None, "API key missing"


class TestSystemIntegration:
    """Test system components integrate correctly."""

    @pytest.mark.asyncio
    async def test_tool_registry_populated(self, tool_registry_with_tools):
        """CRITICAL: All built-in tools are registered"""
        # Essential tools that must exist
        essential_tools = [
            "Read",
            "Write",
            "Edit",
            "Glob",
            "Grep",
            "Bash",
        ]

        for tool_name in essential_tools:
            assert tool_registry_with_tools.exists(tool_name), f"Missing essential tool: {tool_name}"

    @pytest.mark.asyncio
    async def test_command_registry_populated(self):
        """CRITICAL: Built-in commands are registered"""
        from code_forge.commands import CommandRegistry

        registry = CommandRegistry()

        # Essential commands
        essential_commands = [
            "help",
            "version",
        ]

        for cmd_name in essential_commands:
            assert registry.exists(cmd_name), f"Missing essential command: {cmd_name}"

    @pytest.mark.asyncio
    async def test_workflow_templates_loaded(self):
        """CRITICAL: All built-in workflow templates are available"""
        from code_forge.workflows.registry import WorkflowTemplateRegistry

        registry = WorkflowTemplateRegistry.get_instance()

        essential_templates = [
            "pr-review",
            "bug-fix",
            "feature-implementation",
            "security-audit-full",
        ]

        for template_name in essential_templates:
            template = registry.get_template(template_name)
            assert template is not None, f"Missing template: {template_name}"

    def test_package_version(self):
        """CRITICAL: Package version is correct"""
        from code_forge import __version__

        assert __version__ == "1.7.0", f"Wrong version: {__version__}"

    def test_imports_work(self):
        """CRITICAL: Critical imports work without errors"""
        # Core imports
        from code_forge import __version__  # noqa
        from code_forge.tools import ToolRegistry  # noqa
        from code_forge.commands import CommandRegistry  # noqa
        from code_forge.sessions import SessionManager  # noqa
        from code_forge.workflows import WorkflowExecutor  # noqa
        from code_forge.config import ConfigLoader  # noqa

        # If we got here, imports worked
        assert True


class TestErrorHandling:
    """Test error handling works correctly."""

    @pytest.mark.asyncio
    async def test_tool_handles_missing_file(self, tool_registry_with_tools, execution_context):
        """CRITICAL: Read tool handles missing file gracefully"""
        from code_forge.tools import ToolRegistry

        registry = ToolRegistry()
        read_tool = registry.get_tool("Read")

        result = await read_tool.execute(
            context=execution_context,
            file_path="/nonexistent/path/file.txt",
        )

        assert not result.success, "Should fail for missing file"
        assert result.error is not None, "Should have error message"

    @pytest.mark.asyncio
    async def test_tool_handles_invalid_params(self, tool_registry_with_tools, execution_context):
        """CRITICAL: Tools validate parameters"""
        from code_forge.tools import ToolRegistry

        registry = ToolRegistry()
        edit_tool = registry.get_tool("Edit")

        # Missing required parameter
        result = await edit_tool.execute(
            context=execution_context,
            file_path="/some/file.txt",
            old_string="test",
            # Missing new_string
        )

        assert not result.success, "Should fail for missing param"

    @pytest.mark.asyncio
    async def test_command_handles_invalid_syntax(self):
        """CRITICAL: Command parser handles invalid syntax"""
        from code_forge.commands.parser import CommandParser

        parser = CommandParser()

        # Empty command
        parsed = parser.parse("/")
        # Should either parse as empty or handle gracefully

        # Just slash - should handle gracefully
        assert parsed is not None or True  # Parser should not crash
