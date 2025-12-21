"""Workflow template registry and discovery.

This module provides template discovery and management for workflow definitions,
supporting built-in, user-defined, and project-specific workflows.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from code_forge.core.logging import get_logger
from code_forge.workflows.models import WorkflowDefinition
from code_forge.workflows.parser import YAMLWorkflowParser

logger = get_logger(__name__)


class WorkflowTemplateRegistry:
    """Registry for workflow templates with multi-source discovery.

    Discovers and loads workflow templates from:
    - Built-in templates (bundled with Code-Forge)
    - User templates (~/.forge/workflows/)
    - Project templates (.forge/workflows/)

    Singleton pattern ensures consistent template access across the application.

    Attributes:
        templates: Dictionary mapping template names to workflow definitions
    """

    _instance: WorkflowTemplateRegistry | None = None
    _instance_lock = threading.Lock()

    BUILTIN_DIR = Path(__file__).parent / "templates"
    USER_DIR = Path.home() / ".forge" / "workflows"
    PROJECT_DIR_NAME = ".forge/workflows"

    def __init__(self) -> None:
        """Initialize the registry.

        Note: Use get_instance() instead of direct instantiation.
        """
        self.templates: dict[str, WorkflowDefinition] = {}
        self.template_sources: dict[str, str] = {}  # template_name -> source_path
        self._parser = YAMLWorkflowParser()
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> WorkflowTemplateRegistry:
        """Get singleton instance.

        Returns:
            The singleton WorkflowTemplateRegistry instance
        """
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
                cls._instance.discover_templates()
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing)."""
        with cls._instance_lock:
            cls._instance = None

    def discover_templates(self, project_root: Path | str | None = None) -> None:
        """Discover and load templates from all sources.

        Templates are loaded in order of precedence:
        1. Built-in templates (lowest priority)
        2. User templates (overrides built-in)
        3. Project templates (highest priority, overrides all)

        Args:
            project_root: Optional project root for project-specific templates
        """
        with self._lock:
            # Clear existing templates
            self.templates.clear()
            self.template_sources.clear()

            # Load built-in templates
            self._load_templates_from_dir(self.BUILTIN_DIR, "built-in")

            # Load user templates
            if self.USER_DIR.exists():
                self._load_templates_from_dir(self.USER_DIR, "user")

            # Load project templates
            if project_root:
                project_dir = Path(project_root) / self.PROJECT_DIR_NAME
                if project_dir.exists():
                    self._load_templates_from_dir(project_dir, "project")

            logger.info(f"Discovered {len(self.templates)} workflow templates")

    def _load_templates_from_dir(self, directory: Path, source: str) -> None:
        """Load all workflow templates from a directory.

        Args:
            directory: Directory containing YAML workflow files
            source: Source identifier (built-in, user, project)
        """
        if not directory.exists() or not directory.is_dir():
            return

        for yaml_file in directory.glob("*.yaml"):
            try:
                workflow = self._parser.parse_file(yaml_file)
                self.templates[workflow.name] = workflow
                self.template_sources[workflow.name] = f"{source}:{yaml_file}"
                logger.debug(f"Loaded template '{workflow.name}' from {source}")
            except Exception as e:
                logger.warning(f"Failed to load template {yaml_file}: {e}")

    def get_template(self, name: str) -> WorkflowDefinition | None:
        """Get a workflow template by name.

        Args:
            name: Template name

        Returns:
            WorkflowDefinition if found, None otherwise
        """
        with self._lock:
            return self.templates.get(name)

    def list_templates(self) -> list[tuple[str, str, str]]:
        """List all available templates.

        Returns:
            List of tuples (name, description, source)
        """
        with self._lock:
            return [
                (
                    name,
                    workflow.description,
                    self.template_sources.get(name, "unknown"),
                )
                for name, workflow in sorted(self.templates.items())
            ]

    def search_templates(self, query: str) -> list[tuple[str, str, str]]:
        """Search templates by name or description.

        Args:
            query: Search query (case-insensitive)

        Returns:
            List of matching tuples (name, description, source)
        """
        query_lower = query.lower()
        with self._lock:
            return [
                (name, desc, source)
                for name, desc, source in self.list_templates()
                if query_lower in name.lower() or query_lower in desc.lower()
            ]

    def instantiate(
        self,
        name: str,
        parameters: dict[str, Any] | None = None,
    ) -> WorkflowDefinition:
        """Instantiate a workflow from a template.

        Args:
            name: Template name
            parameters: Optional parameters for template substitution

        Returns:
            WorkflowDefinition instance

        Raises:
            ValueError: If template not found
        """
        template = self.get_template(name)
        if template is None:
            raise ValueError(f"Template '{name}' not found")

        # For now, return template as-is
        # Future: Support parameter substitution in inputs
        if parameters:
            logger.debug(f"Template parameters: {parameters} (not yet implemented)")

        return template

    def register_template(
        self,
        workflow: WorkflowDefinition,
        source: str = "runtime",
    ) -> None:
        """Register a workflow template at runtime.

        Args:
            workflow: Workflow definition to register
            source: Source identifier for tracking
        """
        with self._lock:
            self.templates[workflow.name] = workflow
            self.template_sources[workflow.name] = source
            logger.info(f"Registered template '{workflow.name}' from {source}")

    def unregister_template(self, name: str) -> bool:
        """Unregister a workflow template.

        Args:
            name: Template name to remove

        Returns:
            True if template was removed, False if not found
        """
        with self._lock:
            if name in self.templates:
                del self.templates[name]
                del self.template_sources[name]
                logger.info(f"Unregistered template '{name}'")
                return True
            return False

    def reload(self, project_root: Path | str | None = None) -> None:
        """Reload all templates from disk.

        Args:
            project_root: Optional project root for project-specific templates
        """
        logger.info("Reloading workflow templates")
        self.discover_templates(project_root)
