"""Workflow management tool for LLM access.

This module provides a tool that allows LLMs to discover, execute,
and monitor workflow templates.
"""

from __future__ import annotations

from typing import Any

from code_forge.core.logging import get_logger
from code_forge.tools.base import (
    BaseTool,
    ExecutionContext,
    ToolCategory,
    ToolParameter,
    ToolResult,
)
from code_forge.workflows.executor import WorkflowExecutor
from code_forge.workflows.registry import WorkflowTemplateRegistry

logger = get_logger(__name__)


class WorkflowTool(BaseTool):
    """Tool for managing workflow execution from LLMs.

    Provides operations:
    - list: List available workflow templates
    - search: Search templates by query
    - info: Get detailed information about a template
    - run: Execute a workflow template
    - status: Check workflow execution status
    """

    @property
    def name(self) -> str:
        return "Workflow"

    @property
    def description(self) -> str:
        return """Manage multi-agent workflow execution.

Operations:
- list: List all available workflow templates
- search: Search templates by name or description
- info: Get detailed information about a template
- run: Execute a workflow from a template
- status: Check the status of a running workflow

Usage examples:
- List all templates: {"operation": "list"}
- Search templates: {"operation": "search", "query": "security"}
- Get template info: {"operation": "info", "template_name": "pr-review"}
- Run a workflow: {"operation": "run", "template_name": "bug-fix"}
- Check status: {"operation": "status", "workflow_id": "abc123"}"""

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.TASK

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="operation",
                type="string",
                description="Operation to perform: list, search, info, run, status",
                required=True,
                enum=["list", "search", "info", "run", "status"],
            ),
            ToolParameter(
                name="query",
                type="string",
                description="Search query (for 'search' operation)",
                required=False,
            ),
            ToolParameter(
                name="template_name",
                type="string",
                description="Template name (for 'info' and 'run' operations)",
                required=False,
            ),
            ToolParameter(
                name="workflow_id",
                type="string",
                description="Workflow ID (for 'status' operation)",
                required=False,
            ),
        ]

    async def _execute(
        self,
        context: ExecutionContext,  # noqa: ARG002
        **kwargs: Any,
    ) -> ToolResult:
        """Execute workflow tool operation.

        Args:
            context: Execution context
            **kwargs: Tool parameters

        Returns:
            ToolResult with operation output
        """
        operation = kwargs["operation"]

        if operation == "list":
            return await self._list_templates()
        elif operation == "search":
            query = kwargs.get("query")
            if not query:
                return ToolResult.fail("Query is required for search operation")
            return await self._search_templates(query)
        elif operation == "info":
            template_name = kwargs.get("template_name")
            if not template_name:
                return ToolResult.fail(
                    "template_name is required for info operation"
                )
            return await self._get_template_info(template_name)
        elif operation == "run":
            template_name = kwargs.get("template_name")
            if not template_name:
                return ToolResult.fail("template_name is required for run operation")
            return await self._run_workflow(template_name)
        elif operation == "status":
            workflow_id = kwargs.get("workflow_id")
            if not workflow_id:
                return ToolResult.fail("workflow_id is required for status operation")
            return await self._get_workflow_status(workflow_id)
        else:
            return ToolResult.fail(f"Unknown operation: {operation}")

    async def _list_templates(self) -> ToolResult:
        """List all available workflow templates.

        Returns:
            ToolResult with template listing
        """
        registry = WorkflowTemplateRegistry.get_instance()
        templates = registry.list_templates()

        if not templates:
            return ToolResult.ok("No workflow templates available")

        # Format as structured data
        template_list = [
            {
                "name": name,
                "description": description,
                "source": source,
            }
            for name, description, source in templates
        ]

        output = {
            "count": len(templates),
            "templates": template_list,
        }

        return ToolResult.ok(output)

    async def _search_templates(self, query: str) -> ToolResult:
        """Search workflow templates.

        Args:
            query: Search query

        Returns:
            ToolResult with matching templates
        """
        registry = WorkflowTemplateRegistry.get_instance()
        templates = registry.search_templates(query)

        if not templates:
            return ToolResult.ok(f"No templates found matching '{query}'")

        # Format as structured data
        template_list = [
            {
                "name": name,
                "description": description,
                "source": source,
            }
            for name, description, source in templates
        ]

        output = {
            "query": query,
            "count": len(templates),
            "templates": template_list,
        }

        return ToolResult.ok(output)

    async def _get_template_info(self, template_name: str) -> ToolResult:
        """Get detailed template information.

        Args:
            template_name: Name of the template

        Returns:
            ToolResult with template details
        """
        registry = WorkflowTemplateRegistry.get_instance()
        template = registry.get_template(template_name)

        if template is None:
            return ToolResult.fail(f"Template '{template_name}' not found")

        # Format template details
        steps = [
            {
                "id": step.id,
                "agent": step.agent,
                "description": step.description,
                "depends_on": step.depends_on or [],
                "parallel_with": step.parallel_with or [],
                "condition": step.condition,
                "timeout": step.timeout,
            }
            for step in template.steps
        ]

        output = {
            "name": template.name,
            "description": template.description,
            "version": template.version,
            "author": template.author,
            "metadata": template.metadata,
            "steps": steps,
            "total_steps": len(template.steps),
        }

        return ToolResult.ok(output)

    async def _run_workflow(self, template_name: str) -> ToolResult:
        """Run a workflow from template.

        Args:
            template_name: Name of the template to run

        Returns:
            ToolResult with workflow execution status
        """
        registry = WorkflowTemplateRegistry.get_instance()

        try:
            workflow = registry.instantiate(template_name)
        except ValueError as e:
            return ToolResult.fail(str(e))

        # Execute workflow
        executor = WorkflowExecutor()
        try:
            result = await executor.execute(workflow)

            output = {
                "workflow_id": result.workflow_id,
                "workflow_name": result.workflow_name,
                "success": result.success,
                "started_at": str(result.start_time),
                "completed_at": str(result.end_time),
                "error": result.error,
                "steps_completed": result.steps_completed,
                "steps_failed": result.steps_failed,
                "steps_skipped": result.steps_skipped,
                "steps_total": len(result.step_results),
            }

            return ToolResult.ok(output)

        except Exception as e:
            logger.exception("Error executing workflow")
            return ToolResult.fail(f"Error executing workflow: {e}")

    async def _get_workflow_status(self, workflow_id: str) -> ToolResult:
        """Get workflow execution status.

        Args:
            workflow_id: ID of the workflow

        Returns:
            ToolResult with workflow status
        """
        executor = WorkflowExecutor()
        state = executor.get_workflow_state(workflow_id)

        if state is None:
            return ToolResult.fail(f"Workflow '{workflow_id}' not found")

        # Format status
        step_statuses = [
            {
                "id": step_id,
                "success": step_result.success,
                "skipped": step_result.skipped,
                "error": step_result.error,
                "started_at": str(step_result.start_time),
                "completed_at": str(step_result.end_time),
            }
            for step_id, step_result in state.step_results.items()
        ]

        output = {
            "workflow_id": workflow_id,
            "workflow_name": state.definition.name,
            "status": state.status.value,
            "started_at": str(state.start_time),
            "completed_at": str(state.end_time) if state.end_time else None,
            "current_step": state.current_step,
            "steps": step_statuses,
        }

        return ToolResult.ok(output)
