"""
dsa/graph.py
Dependency Graph & Topological Sort implementation for Topic Prerequisites.

Uses Kahn's Algorithm (BFS with indegree) for:
1. Validating prerequisite ordering among study topics.
2. Detecting circular dependencies (cycles).
3. Handling missing or invalid prerequisite references gracefully.

Time Complexity: O(V + E) where V is number of topics and E is number of prerequisite dependencies.
Space Complexity: O(V + E) for adjacency list and in-degree tracking.
"""

from typing import Dict, List, Set, Tuple, Any, Optional
from collections import deque
from .models import Topic


class CircularDependencyError(Exception):
    """Exception raised when a circular dependency (cycle) is detected in topic prerequisites."""

    def __init__(self, message: str, cycle_nodes: Optional[List[Any]] = None):
        super().__init__(message)
        self.cycle_nodes = cycle_nodes or []


class DependencyGraph:
    """
    Directed Graph data structure for topic prerequisites.

    Nodes represent Topic IDs (or topic names).
    A directed edge U -> V means topic U is a PREREQUISITE for topic V (U must be completed before V).
    """

    def __init__(self):
        self.adj: Dict[Any, List[Any]] = {}       # u -> list of dependent topics [v1, v2, ...]
        self.in_degree: Dict[Any, int] = {}       # v -> number of unsatisfied prerequisites
        self.nodes: Set[Any] = set()               # Set of all valid topic identifiers in graph
        self.missing_prerequisites: Dict[Any, List[Any]] = {}  # topic -> list of invalid/missing prereq IDs

    def add_node(self, node_id: Any) -> None:
        """Adds a node to the graph if not already present."""
        if node_id not in self.nodes:
            self.nodes.add(node_id)
            self.adj[node_id] = []
            self.in_degree[node_id] = 0

    def add_edge(self, u: Any, v: Any) -> None:
        """
        Adds a directed edge U -> V (U is prerequisite for V).
        Automatically adds nodes U and V if missing.
        """
        self.add_node(u)
        self.add_node(v)
        # Avoid duplicate edges
        if v not in self.adj[u]:
            self.adj[u].append(v)
            self.in_degree[v] += 1

    @classmethod
    def build_from_topics(cls, topics: List[Topic]) -> Tuple["DependencyGraph", List[str]]:
        """
        Factory method that builds a DependencyGraph from a list of Topic objects.

        Maps each topic to exactly one primary node ID (topic.id if present, else topic.name).
        Maps prerequisite aliases (topic ID or topic name) to primary node IDs.
        Returns (graph, list_of_warning_messages for missing prerequisites).
        """
        graph = cls()
        warnings: List[str] = []

        # Map from any alias identifier (int ID or str Name) -> topic's primary node ID
        identifier_to_primary: Dict[Any, Any] = {}

        # Phase 1: Register primary nodes and alias mappings
        for t in topics:
            primary_id = t.id if t.id is not None else t.name
            graph.add_node(primary_id)

            if t.id is not None:
                identifier_to_primary[t.id] = primary_id
            if t.name:
                identifier_to_primary[t.name] = primary_id

        # Phase 2: Add directed edges for prerequisites (prereq -> topic)
        for t in topics:
            primary_id = t.id if t.id is not None else t.name
            for prereq in t.prerequisites:
                if prereq in identifier_to_primary:
                    prereq_primary = identifier_to_primary[prereq]
                    if prereq_primary != primary_id:
                        graph.add_edge(prereq_primary, primary_id)
                else:
                    # Missing/invalid prerequisite reference
                    warning_msg = f"Topic '{t.name}' references non-existent prerequisite '{prereq}'."
                    warnings.append(warning_msg)
                    if primary_id not in graph.missing_prerequisites:
                        graph.missing_prerequisites[primary_id] = []
                    graph.missing_prerequisites[primary_id].append(prereq)

        return graph, warnings

    def topological_sort(self) -> List[Any]:
        """
        Performs Kahn's Algorithm (BFS with indegrees) to produce a topological ordering of topics.

        Returns:
            List[Any]: List of node identifiers in valid execution order.

        Raises:
            CircularDependencyError: If a cycle / circular dependency is detected.
        """
        in_degree_copy = self.in_degree.copy()
        queue = deque([node for node in self.nodes if in_degree_copy[node] == 0])
        topological_order: List[Any] = []

        while queue:
            u = queue.popleft()
            topological_order.append(u)

            for neighbor in self.adj.get(u, []):
                in_degree_copy[neighbor] -= 1
                if in_degree_copy[neighbor] == 0:
                    queue.append(neighbor)

        # Cycle Detection: if sorted order does not include all nodes, a cycle exists
        if len(topological_order) < len(self.nodes):
            cycle_nodes = [node for node in self.nodes if in_degree_copy[node] > 0]
            raise CircularDependencyError(
                f"Circular dependency detected among topic(s): {cycle_nodes}",
                cycle_nodes=cycle_nodes
            )

        return topological_order

    def detect_cycles(self) -> Optional[List[Any]]:
        """
        Returns list of cycle nodes if a cycle exists, or None if the graph is a DAG (Directed Acyclic Graph).
        """
        try:
            self.topological_sort()
            return None
        except CircularDependencyError as e:
            return e.cycle_nodes
