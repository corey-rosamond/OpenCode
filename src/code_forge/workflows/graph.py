"""Workflow graph construction and validation.

This module provides DAG (Directed Acyclic Graph) construction and validation
for workflows, including cycle detection and topological sorting.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import TYPE_CHECKING

from code_forge.core.logging import get_logger

if TYPE_CHECKING:
    from code_forge.workflows.models import WorkflowDefinition, WorkflowStep

logger = get_logger(__name__)


class WorkflowGraph:
    """Directed acyclic graph representation of a workflow.

    Represents workflow steps as nodes and dependencies as directed edges.
    Provides methods for querying the graph structure.

    Attributes:
        steps: Map of step ID to WorkflowStep
        adjacency: Adjacency list (step_id -> list of dependent step IDs)
        reverse_adjacency: Reverse adjacency list (step_id -> list of dependency step IDs)
    """

    def __init__(self) -> None:
        """Initialize an empty workflow graph."""
        self.steps: dict[str, WorkflowStep] = {}
        self.adjacency: dict[str, list[str]] = defaultdict(list)
        self.reverse_adjacency: dict[str, list[str]] = defaultdict(list)

    def add_step(self, step: WorkflowStep) -> None:
        """Add a step (node) to the graph.

        Args:
            step: The workflow step to add

        Raises:
            ValueError: If a step with this ID already exists
        """
        if step.id in self.steps:
            raise ValueError(f"Step with ID '{step.id}' already exists")

        self.steps[step.id] = step

        # Initialize adjacency lists for this step
        if step.id not in self.adjacency:
            self.adjacency[step.id] = []
        if step.id not in self.reverse_adjacency:
            self.reverse_adjacency[step.id] = []

    def add_dependency(self, from_step: str, to_step: str) -> None:
        """Add a dependency edge (from_step must complete before to_step).

        Args:
            from_step: ID of the step that must complete first
            to_step: ID of the step that depends on from_step

        Raises:
            ValueError: If either step doesn't exist
        """
        if from_step not in self.steps:
            raise ValueError(f"Step '{from_step}' does not exist")
        if to_step not in self.steps:
            raise ValueError(f"Step '{to_step}' does not exist")

        self.adjacency[from_step].append(to_step)
        self.reverse_adjacency[to_step].append(from_step)

    def get_dependencies(self, step_id: str) -> list[str]:
        """Get the list of steps that the given step depends on.

        Args:
            step_id: ID of the step

        Returns:
            List of step IDs that must complete before this step

        Raises:
            ValueError: If step doesn't exist
        """
        if step_id not in self.steps:
            raise ValueError(f"Step '{step_id}' does not exist")

        return list(self.reverse_adjacency[step_id])

    def get_dependents(self, step_id: str) -> list[str]:
        """Get the list of steps that depend on the given step.

        Args:
            step_id: ID of the step

        Returns:
            List of step IDs that depend on this step

        Raises:
            ValueError: If step doesn't exist
        """
        if step_id not in self.steps:
            raise ValueError(f"Step '{step_id}' does not exist")

        return list(self.adjacency[step_id])

    def get_parallel_candidates(self, step_id: str) -> list[str]:
        """Get steps that can potentially run in parallel with this step.

        Two steps can run in parallel if:
        1. They have the same dependencies
        2. Neither depends on the other
        3. They are marked with parallel_with hints

        Args:
            step_id: ID of the step

        Returns:
            List of step IDs that can run in parallel

        Raises:
            ValueError: If step doesn't exist
        """
        if step_id not in self.steps:
            raise ValueError(f"Step '{step_id}' does not exist")

        step = self.steps[step_id]
        parallel = []

        # Check parallel_with hints first
        for candidate_id in step.parallel_with:
            if candidate_id in self.steps:
                parallel.append(candidate_id)

        return parallel

    @classmethod
    def from_definition(cls, definition: WorkflowDefinition) -> WorkflowGraph:
        """Build a graph from a workflow definition.

        Args:
            definition: The workflow definition

        Returns:
            Constructed workflow graph

        Raises:
            ValueError: If the workflow definition is invalid
        """
        graph = cls()

        # Add all steps as nodes
        for step in definition.steps:
            graph.add_step(step)

        # Add dependency edges
        for step in definition.steps:
            for dep_id in step.depends_on:
                graph.add_dependency(dep_id, step.id)

        return graph


class GraphValidator:
    """Validates workflow graphs for correctness.

    Performs validation including:
    - Cycle detection
    - Orphaned node detection
    - Reference validation
    """

    def __init__(self, graph: WorkflowGraph) -> None:
        """Initialize validator with a graph.

        Args:
            graph: The workflow graph to validate
        """
        self.graph = graph

    def validate(self) -> None:
        """Validate the workflow graph.

        Raises:
            ValueError: If the graph is invalid
        """
        self._check_for_cycles()
        self._check_dependencies_exist()
        logger.debug(f"Graph validation passed for {len(self.graph.steps)} steps")

    def _check_for_cycles(self) -> None:
        """Check for cycles in the graph using DFS.

        Raises:
            ValueError: If a cycle is detected
        """
        # Track visit status: 0 = unvisited, 1 = visiting, 2 = visited
        visit_status: dict[str, int] = {step_id: 0 for step_id in self.graph.steps}
        parent: dict[str, str | None] = {step_id: None for step_id in self.graph.steps}

        def dfs(node: str) -> None:
            visit_status[node] = 1  # Mark as visiting

            for neighbor in self.graph.adjacency[node]:
                if visit_status[neighbor] == 1:
                    # Found a back edge - cycle detected
                    cycle_path = self._build_cycle_path(node, neighbor, parent)
                    raise ValueError(f"Cycle detected in workflow: {cycle_path}")
                elif visit_status[neighbor] == 0:
                    parent[neighbor] = node
                    dfs(neighbor)

            visit_status[node] = 2  # Mark as visited

        # Run DFS from each unvisited node
        for node in self.graph.steps:
            if visit_status[node] == 0:
                dfs(node)

    def _build_cycle_path(self, start: str, end: str, parent: dict[str, str | None]) -> str:
        """Build a human-readable cycle path.

        Args:
            start: Start of the cycle
            end: End of the cycle (back edge target)
            parent: Parent pointers from DFS

        Returns:
            String representation of the cycle path
        """
        path = [end]
        current = start
        while current is not None and current != end:
            path.append(current)
            current = parent.get(current)
        path.append(end)
        return " -> ".join(reversed(path))

    def _check_dependencies_exist(self) -> None:
        """Check that all referenced dependencies exist.

        Raises:
            ValueError: If a referenced step doesn't exist
        """
        for step in self.graph.steps.values():
            for dep_id in step.depends_on:
                if dep_id not in self.graph.steps:
                    raise ValueError(
                        f"Step '{step.id}' depends on non-existent step '{dep_id}'"
                    )

            for parallel_id in step.parallel_with:
                if parallel_id not in self.graph.steps:
                    logger.warning(
                        f"Step '{step.id}' references non-existent parallel step '{parallel_id}'"
                    )


class TopologicalSorter:
    """Performs topological sort on a workflow graph.

    Uses Kahn's algorithm to produce a valid execution order for workflow steps.
    """

    def __init__(self, graph: WorkflowGraph) -> None:
        """Initialize sorter with a graph.

        Args:
            graph: The workflow graph to sort
        """
        self.graph = graph

    def sort(self) -> list[str]:
        """Compute a topological ordering of the workflow steps.

        Returns:
            List of step IDs in a valid execution order

        Raises:
            ValueError: If the graph contains a cycle
        """
        # Calculate in-degree for each node
        in_degree: dict[str, int] = {
            step_id: len(self.graph.reverse_adjacency[step_id])
            for step_id in self.graph.steps
        }

        # Queue of nodes with no incoming edges
        queue: deque[str] = deque(
            [step_id for step_id, degree in in_degree.items() if degree == 0]
        )

        result: list[str] = []

        while queue:
            # Remove node with no incoming edges
            current = queue.popleft()
            result.append(current)

            # Reduce in-degree for neighbors
            for neighbor in self.graph.adjacency[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # If not all nodes were visited, there's a cycle
        if len(result) != len(self.graph.steps):
            unvisited = [step_id for step_id in self.graph.steps if step_id not in result]
            raise ValueError(
                f"Cannot perform topological sort - cycle detected. Unvisited nodes: {unvisited}"
            )

        return result

    def get_execution_batches(self) -> list[list[str]]:
        """Get steps grouped into parallel execution batches.

        Steps in the same batch have no dependencies on each other and can
        run in parallel.

        Returns:
            List of batches, where each batch is a list of step IDs that
            can execute in parallel

        Raises:
            ValueError: If the graph contains a cycle
        """
        # Calculate in-degree for each node
        in_degree: dict[str, int] = {
            step_id: len(self.graph.reverse_adjacency[step_id])
            for step_id in self.graph.steps
        }

        batches: list[list[str]] = []
        remaining = set(self.graph.steps.keys())

        while remaining:
            # Find all nodes with in-degree 0
            batch = [step_id for step_id in remaining if in_degree[step_id] == 0]

            if not batch:
                # No nodes with in-degree 0 means there's a cycle
                raise ValueError(f"Cannot create execution batches - cycle detected. Remaining nodes: {remaining}")

            batches.append(batch)

            # Remove batch from remaining and update in-degrees
            for step_id in batch:
                remaining.remove(step_id)
                for neighbor in self.graph.adjacency[step_id]:
                    in_degree[neighbor] -= 1

        return batches
