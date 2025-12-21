"""Workflow management slash commands.

This module provides /workflow command with subcommands for managing
workflow execution, monitoring, and control.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from code_forge.commands.base import (
    Command,
    CommandArgument,
    CommandCategory,
    CommandResult,
)
from code_forge.core.logging import get_logger
from code_forge.workflows.executor import WorkflowExecutor
from code_forge.workflows.registry import WorkflowTemplateRegistry

if TYPE_CHECKING:
    from code_forge.commands.executor import CommandContext
    from code_forge.commands.parser import ParsedCommand

logger = get_logger(__name__)


class WorkflowListCommand(Command):
    """List available workflow templates."""

    name = "workflow-list"
    aliases = ["wf-list"]
    description = "List all available workflow templates"
    usage = "/workflow list [query]"
    category = CommandCategory.WORKFLOW
    arguments = [
        CommandArgument(
            name="query",
            description="Optional search query to filter templates",
            required=False,
        ),
    ]

    async def execute(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """List workflow templates.

        Args:
            parsed: Parsed command with arguments
            context: Command execution context

        Returns:
            CommandResult with template listing
        """
        registry = WorkflowTemplateRegistry.get_instance()
        query = parsed.get_arg(0)

        if query:
            templates = registry.search_templates(query)
            header = f"Workflow templates matching '{query}':"
        else:
            templates = registry.list_templates()
            header = "Available workflow templates:"

        if not templates:
            return CommandResult.ok("No workflow templates found")

        # Format output
        lines = [header, ""]
        for name, description, source in templates:
            lines.append(f"  {name}")
            lines.append(f"    {description}")
            lines.append(f"    Source: {source}")
            lines.append("")

        return CommandResult.ok("\n".join(lines))


class WorkflowRunCommand(Command):
    """Run a workflow from template."""

    name = "workflow-run"
    aliases = ["wf-run"]
    description = "Run a workflow from a template"
    usage = "/workflow run <template_name>"
    category = CommandCategory.WORKFLOW
    arguments = [
        CommandArgument(
            name="template_name",
            description="Name of the workflow template to run",
            required=True,
        ),
    ]

    async def execute(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Run a workflow.

        Args:
            parsed: Parsed command with arguments
            context: Command execution context

        Returns:
            CommandResult with execution status
        """
        template_name = parsed.get_arg(0)
        if not template_name:
            return CommandResult.fail("Template name is required")

        # Get template
        registry = WorkflowTemplateRegistry.get_instance()
        try:
            workflow = registry.instantiate(template_name)
        except ValueError as e:
            return CommandResult.fail(str(e))

        # Execute workflow
        executor = WorkflowExecutor()
        try:
            # Note: This would typically run in background
            # For now, we'll run it synchronously
            result = await executor.execute(workflow)

            if result.success:
                return CommandResult.ok(
                    f"Workflow '{template_name}' completed successfully\n"
                    f"Workflow ID: {result.workflow_id}"
                )
            else:
                return CommandResult.fail(
                    f"Workflow '{template_name}' failed\n"
                    f"Workflow ID: {result.workflow_id}\n"
                    f"Error: {result.error}"
                )

        except Exception as e:
            logger.exception("Error executing workflow")
            return CommandResult.fail(f"Error executing workflow: {e}")


class WorkflowStatusCommand(Command):
    """Check workflow execution status."""

    name = "workflow-status"
    aliases = ["wf-status"]
    description = "Check the status of a running or completed workflow"
    usage = "/workflow status <workflow_id>"
    category = CommandCategory.WORKFLOW
    arguments = [
        CommandArgument(
            name="workflow_id",
            description="ID of the workflow to check",
            required=True,
        ),
    ]

    async def execute(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Check workflow status.

        Args:
            parsed: Parsed command with arguments
            context: Command execution context

        Returns:
            CommandResult with workflow status
        """
        workflow_id = parsed.get_arg(0)
        if not workflow_id:
            return CommandResult.fail("Workflow ID is required")

        executor = WorkflowExecutor()
        state = executor.get_workflow_state(workflow_id)

        if state is None:
            return CommandResult.fail(f"Workflow '{workflow_id}' not found")

        # Format status output
        lines = [
            f"Workflow: {state.definition.name}",
            f"Status: {state.status.value}",
            f"Started: {state.start_time}",
            "",
            "Steps:",
        ]

        for step_id, step_result in state.step_results.items():
            status_icon = "✓" if step_result.success else "✗"
            status_text = "completed" if step_result.success else "failed"
            if step_result.skipped:
                status_icon = "-"
                status_text = "skipped"
            lines.append(f"  {status_icon} {step_id}: {status_text}")

        if state.current_step:
            lines.append("")
            lines.append(f"Current step: {state.current_step}")

        if state.end_time:
            lines.append("")
            lines.append(f"Completed: {state.end_time}")

        return CommandResult.ok("\n".join(lines))


class WorkflowResumeCommand(Command):
    """Resume a failed workflow."""

    name = "workflow-resume"
    aliases = ["wf-resume"]
    description = "Resume a failed or paused workflow"
    usage = "/workflow resume <workflow_id>"
    category = CommandCategory.WORKFLOW
    arguments = [
        CommandArgument(
            name="workflow_id",
            description="ID of the workflow to resume",
            required=True,
        ),
    ]

    async def execute(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Resume a workflow.

        Args:
            parsed: Parsed command with arguments
            context: Command execution context

        Returns:
            CommandResult with resume status
        """
        workflow_id = parsed.get_arg(0)
        if not workflow_id:
            return CommandResult.fail("Workflow ID is required")

        executor = WorkflowExecutor()
        state = executor.get_workflow_state(workflow_id)

        if state is None:
            return CommandResult.fail(f"Workflow '{workflow_id}' not found")

        if state.status.value not in ("failed", "paused"):
            return CommandResult.fail(
                f"Cannot resume workflow with status: {state.status.value}"
            )

        try:
            # Resume execution
            result = await executor.resume(workflow_id)

            if result.success:
                return CommandResult.ok(
                    f"Workflow '{workflow_id}' resumed and completed successfully"
                )
            else:
                return CommandResult.fail(
                    f"Workflow '{workflow_id}' resumed but failed\n"
                    f"Error: {result.error}"
                )

        except Exception as e:
            logger.exception("Error resuming workflow")
            return CommandResult.fail(f"Error resuming workflow: {e}")


class WorkflowCancelCommand(Command):
    """Cancel a running workflow."""

    name = "workflow-cancel"
    aliases = ["wf-cancel"]
    description = "Cancel a running workflow"
    usage = "/workflow cancel <workflow_id>"
    category = CommandCategory.WORKFLOW
    arguments = [
        CommandArgument(
            name="workflow_id",
            description="ID of the workflow to cancel",
            required=True,
        ),
    ]

    async def execute(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Cancel a workflow.

        Args:
            parsed: Parsed command with arguments
            context: Command execution context

        Returns:
            CommandResult with cancellation status
        """
        workflow_id = parsed.get_arg(0)
        if not workflow_id:
            return CommandResult.fail("Workflow ID is required")

        executor = WorkflowExecutor()
        state = executor.get_workflow_state(workflow_id)

        if state is None:
            return CommandResult.fail(f"Workflow '{workflow_id}' not found")

        if state.status.value not in ("running", "paused"):
            return CommandResult.fail(
                f"Cannot cancel workflow with status: {state.status.value}"
            )

        try:
            success = await executor.cancel(workflow_id)

            if success:
                return CommandResult.ok(f"Workflow '{workflow_id}' cancelled")
            else:
                return CommandResult.fail(f"Failed to cancel workflow '{workflow_id}'")

        except Exception as e:
            logger.exception("Error cancelling workflow")
            return CommandResult.fail(f"Error cancelling workflow: {e}")


class WorkflowCommand(Command):
    """Main workflow command with subcommands."""

    name = "workflow"
    aliases = ["wf"]
    description = "Manage workflow execution (list, run, status, resume, cancel)"
    usage = "/workflow <subcommand> [args]"
    category = CommandCategory.WORKFLOW
    arguments = [
        CommandArgument(
            name="subcommand",
            description="Subcommand: list, run, status, resume, cancel",
            required=True,
        ),
    ]

    def __init__(self) -> None:
        """Initialize workflow command with subcommands."""
        super().__init__()
        self._subcommands: dict[str, Command] = {
            "list": WorkflowListCommand(),
            "run": WorkflowRunCommand(),
            "status": WorkflowStatusCommand(),
            "resume": WorkflowResumeCommand(),
            "cancel": WorkflowCancelCommand(),
        }

    async def execute(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
    ) -> CommandResult:
        """Execute workflow subcommand.

        Args:
            parsed: Parsed command with arguments
            context: Command execution context

        Returns:
            CommandResult from subcommand execution
        """
        subcommand = parsed.get_arg(0)

        if not subcommand:
            return CommandResult.fail(
                "Subcommand required. Usage: /workflow <list|run|status|resume|cancel>"
            )

        if subcommand not in self._subcommands:
            return CommandResult.fail(
                f"Unknown subcommand: {subcommand}\n"
                "Available: list, run, status, resume, cancel"
            )

        # Delegate to subcommand
        cmd = self._subcommands[subcommand]
        return await cmd.execute(parsed, context)
