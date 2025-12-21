"""Unit tests for workflow graph construction and validation."""

import pytest

from code_forge.workflows.graph import GraphValidator, TopologicalSorter, WorkflowGraph
from code_forge.workflows.models import WorkflowDefinition, WorkflowStep


class TestWorkflowGraph:
    """Tests for WorkflowGraph class."""

    def test_create_empty_graph(self):
        """Given no steps, creates empty WorkflowGraph"""
        graph = WorkflowGraph()

        assert len(graph.steps) == 0
        assert len(graph.adjacency) == 0
        assert len(graph.reverse_adjacency) == 0

    def test_add_single_step(self):
        """Given single step, adds to graph"""
        graph = WorkflowGraph()
        step = WorkflowStep(id="step1", agent="test", description="Test")

        graph.add_step(step)

        assert "step1" in graph.steps
        assert graph.steps["step1"] == step

    def test_reject_duplicate_step_id(self):
        """Given duplicate step ID, raises ValueError"""
        graph = WorkflowGraph()
        step1 = WorkflowStep(id="step1", agent="test", description="Test 1")
        step2 = WorkflowStep(id="step1", agent="test", description="Test 2")

        graph.add_step(step1)

        with pytest.raises(ValueError, match="Step with ID 'step1' already exists"):
            graph.add_step(step2)

    def test_add_dependency(self):
        """Given two steps, adds dependency edge"""
        graph = WorkflowGraph()
        step1 = WorkflowStep(id="step1", agent="test", description="Test 1")
        step2 = WorkflowStep(id="step2", agent="test", description="Test 2")

        graph.add_step(step1)
        graph.add_step(step2)
        graph.add_dependency("step1", "step2")

        assert "step2" in graph.adjacency["step1"]
        assert "step1" in graph.reverse_adjacency["step2"]

    def test_reject_dependency_to_nonexistent_step(self):
        """Given dependency to non-existent step, raises ValueError"""
        graph = WorkflowGraph()
        step1 = WorkflowStep(id="step1", agent="test", description="Test")

        graph.add_step(step1)

        with pytest.raises(ValueError, match="Step 'step2' does not exist"):
            graph.add_dependency("step1", "step2")

    def test_get_dependencies(self):
        """Given step with dependencies, returns dependency list"""
        graph = WorkflowGraph()
        step1 = WorkflowStep(id="step1", agent="test", description="Test 1")
        step2 = WorkflowStep(id="step2", agent="test", description="Test 2")
        step3 = WorkflowStep(id="step3", agent="test", description="Test 3")

        graph.add_step(step1)
        graph.add_step(step2)
        graph.add_step(step3)
        graph.add_dependency("step1", "step3")
        graph.add_dependency("step2", "step3")

        deps = graph.get_dependencies("step3")

        assert set(deps) == {"step1", "step2"}

    def test_get_dependents(self):
        """Given step with dependents, returns dependent list"""
        graph = WorkflowGraph()
        step1 = WorkflowStep(id="step1", agent="test", description="Test 1")
        step2 = WorkflowStep(id="step2", agent="test", description="Test 2")
        step3 = WorkflowStep(id="step3", agent="test", description="Test 3")

        graph.add_step(step1)
        graph.add_step(step2)
        graph.add_step(step3)
        graph.add_dependency("step1", "step2")
        graph.add_dependency("step1", "step3")

        dependents = graph.get_dependents("step1")

        assert set(dependents) == {"step2", "step3"}

    def test_get_parallel_candidates(self):
        """Given step with parallel hints, returns parallel candidates"""
        graph = WorkflowGraph()
        step1 = WorkflowStep(
            id="step1",
            agent="test",
            description="Test 1",
            parallel_with=["step2", "step3"],
        )
        step2 = WorkflowStep(id="step2", agent="test", description="Test 2")
        step3 = WorkflowStep(id="step3", agent="test", description="Test 3")

        graph.add_step(step1)
        graph.add_step(step2)
        graph.add_step(step3)

        candidates = graph.get_parallel_candidates("step1")

        assert set(candidates) == {"step2", "step3"}

    def test_from_definition_simple(self):
        """Given simple workflow definition, builds graph"""
        steps = [
            WorkflowStep(id="step1", agent="plan", description="Plan"),
            WorkflowStep(
                id="step2",
                agent="review",
                description="Review",
                depends_on=["step1"],
            ),
        ]
        definition = WorkflowDefinition(
            name="test",
            description="Test",
            version="1.0.0",
            steps=steps,
        )

        graph = WorkflowGraph.from_definition(definition)

        assert len(graph.steps) == 2
        assert "step1" in graph.steps
        assert "step2" in graph.steps
        assert "step1" in graph.get_dependencies("step2")


class TestGraphValidator:
    """Tests for GraphValidator class."""

    def test_validate_simple_graph(self):
        """Given valid acyclic graph, validation passes"""
        graph = WorkflowGraph()
        step1 = WorkflowStep(id="step1", agent="test", description="Test 1")
        step2 = WorkflowStep(
            id="step2",
            agent="test",
            description="Test 2",
            depends_on=["step1"],
        )

        graph.add_step(step1)
        graph.add_step(step2)
        graph.add_dependency("step1", "step2")

        validator = GraphValidator(graph)
        validator.validate()  # Should not raise

    def test_detect_simple_cycle(self):
        """Given simple cycle A→B→A, detects cycle"""
        graph = WorkflowGraph()
        step1 = WorkflowStep(id="A", agent="test", description="Test A")
        step2 = WorkflowStep(id="B", agent="test", description="Test B")

        graph.add_step(step1)
        graph.add_step(step2)
        graph.add_dependency("A", "B")
        graph.add_dependency("B", "A")

        validator = GraphValidator(graph)

        with pytest.raises(ValueError, match="Cycle detected"):
            validator.validate()

    def test_detect_self_reference_cycle(self):
        """Given self-referencing step A→A, detects cycle"""
        graph = WorkflowGraph()
        step = WorkflowStep(id="A", agent="test", description="Test")

        graph.add_step(step)
        graph.add_dependency("A", "A")

        validator = GraphValidator(graph)

        with pytest.raises(ValueError, match="Cycle detected"):
            validator.validate()

    def test_detect_complex_cycle(self):
        """Given complex cycle A→B→C→D→B, detects cycle"""
        graph = WorkflowGraph()
        steps = [
            WorkflowStep(id="A", agent="test", description="Test A"),
            WorkflowStep(id="B", agent="test", description="Test B"),
            WorkflowStep(id="C", agent="test", description="Test C"),
            WorkflowStep(id="D", agent="test", description="Test D"),
        ]

        for step in steps:
            graph.add_step(step)

        graph.add_dependency("A", "B")
        graph.add_dependency("B", "C")
        graph.add_dependency("C", "D")
        graph.add_dependency("D", "B")  # Cycle

        validator = GraphValidator(graph)

        with pytest.raises(ValueError, match="Cycle detected"):
            validator.validate()

    def test_check_nonexistent_dependency(self):
        """Given dependency on non-existent step, raises ValueError"""
        graph = WorkflowGraph()
        step = WorkflowStep(
            id="step1",
            agent="test",
            description="Test",
            depends_on=["nonexistent"],
        )

        graph.add_step(step)

        validator = GraphValidator(graph)

        with pytest.raises(ValueError, match="depends on non-existent step"):
            validator.validate()


class TestTopologicalSorter:
    """Tests for TopologicalSorter class."""

    def test_sort_linear_graph(self):
        """Given linear graph A→B→C, returns [A, B, C]"""
        graph = WorkflowGraph()
        steps = [
            WorkflowStep(id="A", agent="test", description="Test A"),
            WorkflowStep(id="B", agent="test", description="Test B"),
            WorkflowStep(id="C", agent="test", description="Test C"),
        ]

        for step in steps:
            graph.add_step(step)

        graph.add_dependency("A", "B")
        graph.add_dependency("B", "C")

        sorter = TopologicalSorter(graph)
        result = sorter.sort()

        assert result == ["A", "B", "C"]

    def test_sort_diamond_pattern(self):
        """Given diamond A→(B,C)→D, returns valid order"""
        graph = WorkflowGraph()
        steps = [
            WorkflowStep(id="A", agent="test", description="Test A"),
            WorkflowStep(id="B", agent="test", description="Test B"),
            WorkflowStep(id="C", agent="test", description="Test C"),
            WorkflowStep(id="D", agent="test", description="Test D"),
        ]

        for step in steps:
            graph.add_step(step)

        graph.add_dependency("A", "B")
        graph.add_dependency("A", "C")
        graph.add_dependency("B", "D")
        graph.add_dependency("C", "D")

        sorter = TopologicalSorter(graph)
        result = sorter.sort()

        # A must come first, D must come last
        assert result[0] == "A"
        assert result[3] == "D"
        # B and C can be in any order but must be between A and D
        assert set(result[1:3]) == {"B", "C"}

    def test_sort_complex_graph(self):
        """Given complex graph, returns valid topological order"""
        graph = WorkflowGraph()
        steps = [
            WorkflowStep(id="A", agent="test", description="Test A"),
            WorkflowStep(id="B", agent="test", description="Test B"),
            WorkflowStep(id="C", agent="test", description="Test C"),
            WorkflowStep(id="D", agent="test", description="Test D"),
            WorkflowStep(id="E", agent="test", description="Test E"),
        ]

        for step in steps:
            graph.add_step(step)

        # A → B → D
        # A → C → D
        # C → E
        graph.add_dependency("A", "B")
        graph.add_dependency("A", "C")
        graph.add_dependency("B", "D")
        graph.add_dependency("C", "D")
        graph.add_dependency("C", "E")

        sorter = TopologicalSorter(graph)
        result = sorter.sort()

        # Verify A comes before all others
        assert result.index("A") < result.index("B")
        assert result.index("A") < result.index("C")
        assert result.index("A") < result.index("D")
        assert result.index("A") < result.index("E")

        # Verify B comes before D
        assert result.index("B") < result.index("D")

        # Verify C comes before D and E
        assert result.index("C") < result.index("D")
        assert result.index("C") < result.index("E")

    def test_reject_cyclic_graph(self):
        """Given cyclic graph, raises ValueError"""
        graph = WorkflowGraph()
        steps = [
            WorkflowStep(id="A", agent="test", description="Test A"),
            WorkflowStep(id="B", agent="test", description="Test B"),
        ]

        for step in steps:
            graph.add_step(step)

        graph.add_dependency("A", "B")
        graph.add_dependency("B", "A")

        sorter = TopologicalSorter(graph)

        with pytest.raises(ValueError, match="cycle detected"):
            sorter.sort()

    def test_get_execution_batches_linear(self):
        """Given linear graph, returns sequential batches"""
        graph = WorkflowGraph()
        steps = [
            WorkflowStep(id="A", agent="test", description="Test A"),
            WorkflowStep(id="B", agent="test", description="Test B"),
            WorkflowStep(id="C", agent="test", description="Test C"),
        ]

        for step in steps:
            graph.add_step(step)

        graph.add_dependency("A", "B")
        graph.add_dependency("B", "C")

        sorter = TopologicalSorter(graph)
        batches = sorter.get_execution_batches()

        assert batches == [["A"], ["B"], ["C"]]

    def test_get_execution_batches_parallel(self):
        """Given parallel steps, returns parallel batches"""
        graph = WorkflowGraph()
        steps = [
            WorkflowStep(id="A", agent="test", description="Test A"),
            WorkflowStep(id="B", agent="test", description="Test B"),
            WorkflowStep(id="C", agent="test", description="Test C"),
            WorkflowStep(id="D", agent="test", description="Test D"),
        ]

        for step in steps:
            graph.add_step(step)

        # A → (B, C) → D
        graph.add_dependency("A", "B")
        graph.add_dependency("A", "C")
        graph.add_dependency("B", "D")
        graph.add_dependency("C", "D")

        sorter = TopologicalSorter(graph)
        batches = sorter.get_execution_batches()

        assert len(batches) == 3
        assert batches[0] == ["A"]
        assert set(batches[1]) == {"B", "C"}
        assert batches[2] == ["D"]

    def test_get_execution_batches_complex(self):
        """Given complex graph, returns correct parallel batches"""
        graph = WorkflowGraph()
        steps = [
            WorkflowStep(id="A", agent="test", description="Test A"),
            WorkflowStep(id="B", agent="test", description="Test B"),
            WorkflowStep(id="C", agent="test", description="Test C"),
            WorkflowStep(id="D", agent="test", description="Test D"),
            WorkflowStep(id="E", agent="test", description="Test E"),
            WorkflowStep(id="F", agent="test", description="Test F"),
        ]

        for step in steps:
            graph.add_step(step)

        # A → (B, C)
        # B → D
        # C → (E, F)
        graph.add_dependency("A", "B")
        graph.add_dependency("A", "C")
        graph.add_dependency("B", "D")
        graph.add_dependency("C", "E")
        graph.add_dependency("C", "F")

        sorter = TopologicalSorter(graph)
        batches = sorter.get_execution_batches()

        assert len(batches) == 3
        assert batches[0] == ["A"]
        assert set(batches[1]) == {"B", "C"}
        assert set(batches[2]) == {"D", "E", "F"}

    def test_reject_cyclic_graph_in_batches(self):
        """Given cyclic graph for batches, raises ValueError"""
        graph = WorkflowGraph()
        steps = [
            WorkflowStep(id="A", agent="test", description="Test A"),
            WorkflowStep(id="B", agent="test", description="Test B"),
        ]

        for step in steps:
            graph.add_step(step)

        graph.add_dependency("A", "B")
        graph.add_dependency("B", "A")

        sorter = TopologicalSorter(graph)

        with pytest.raises(ValueError, match="cycle detected"):
            sorter.get_execution_batches()
