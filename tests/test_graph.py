"""
tests/test_graph.py
Unit tests for DependencyGraph and Topological Sort (Kahn's Algorithm).
"""

import pytest
from dsa.models import Topic
from dsa.graph import DependencyGraph, CircularDependencyError


def test_basic_topological_ordering():
    """
    Verifies basic linear topological ordering for A -> B -> C.
    A must appear before B, and B must appear before C.
    """
    topics = [
        Topic(id=1, name="Arrays", prerequisites=[]),
        Topic(id=2, name="Searching", prerequisites=[1]),
        Topic(id=3, name="Trees", prerequisites=[2]),
    ]

    graph, warnings = DependencyGraph.build_from_topics(topics)
    assert len(warnings) == 0

    order = graph.topological_sort()
    assert order.index(1) < order.index(2)
    assert order.index(2) < order.index(3)


def test_multiple_independent_topics():
    """
    Verifies topological sort with multiple independent topics (no dependencies).
    All topics must be included in the ordering.
    """
    topics = [
        Topic(id=101, name="Topic A"),
        Topic(id=102, name="Topic B"),
        Topic(id=103, name="Topic C"),
    ]

    graph, warnings = DependencyGraph.build_from_topics(topics)
    assert len(warnings) == 0

    order = graph.topological_sort()
    assert len(order) == 3
    assert set(order) == {101, 102, 103}


def test_prerequisite_chains():
    """
    Verifies linear chain of length 4: 1 -> 2 -> 3 -> 4.
    """
    topics = [
        Topic(id=4, name="Level 4", prerequisites=[3]),
        Topic(id=2, name="Level 2", prerequisites=[1]),
        Topic(id=1, name="Level 1", prerequisites=[]),
        Topic(id=3, name="Level 3", prerequisites=[2]),
    ]

    graph, warnings = DependencyGraph.build_from_topics(topics)
    order = graph.topological_sort()

    assert order == [1, 2, 3, 4]


def test_multiple_prerequisites():
    """
    Verifies topic with multiple prerequisites (A, B -> C).
    Topic C must appear after BOTH Topic A and Topic B.
    """
    topics = [
        Topic(id=1, name="HTML"),
        Topic(id=2, name="CSS"),
        Topic(id=3, name="Web App", prerequisites=[1, 2]),
    ]

    graph, warnings = DependencyGraph.build_from_topics(topics)
    order = graph.topological_sort()

    assert order.index(1) < order.index(3)
    assert order.index(2) < order.index(3)


def test_circular_dependency_detection():
    """
    Verifies that circular dependencies (A -> B -> C -> A) trigger CircularDependencyError
    and report cycle nodes clearly.
    """
    topics = [
        Topic(id=1, name="Topic A", prerequisites=[3]),
        Topic(id=2, name="Topic B", prerequisites=[1]),
        Topic(id=3, name="Topic C", prerequisites=[2]),
    ]

    graph, warnings = DependencyGraph.build_from_topics(topics)

    with pytest.raises(CircularDependencyError) as exc_info:
        graph.topological_sort()

    err = exc_info.value
    assert set(err.cycle_nodes) == {1, 2, 3}

    # Verify detect_cycles helper
    cycle_nodes = graph.detect_cycles()
    assert cycle_nodes is not None
    assert set(cycle_nodes) == {1, 2, 3}


def test_invalid_or_missing_topic_dependency():
    """
    Verifies handling of invalid/missing prerequisite IDs (e.g. topic references ID 999 which does not exist).
    Should generate a clear warning message without crashing.
    """
    topics = [
        Topic(id=1, name="Valid Topic", prerequisites=[999]),  # 999 does not exist
    ]

    graph, warnings = DependencyGraph.build_from_topics(topics)

    assert len(warnings) == 1
    assert "references non-existent prerequisite '999'" in warnings[0]
    assert 1 in graph.missing_prerequisites
    assert 999 in graph.missing_prerequisites[1]

    # Topological sort still runs safely for valid nodes
    order = graph.topological_sort()
    assert 1 in order
