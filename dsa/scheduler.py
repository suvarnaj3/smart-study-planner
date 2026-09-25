"""
dsa/scheduler.py
Greedy Study Slot Scheduler using Priority Queue (Max Heap) with Graph Prerequisite Resolution.

Algorithm Strategy:
1. Validate topic prerequisites using DependencyGraph and Kahn's Topological Sort algorithm.
2. Filter all uncompleted topics with remaining study hours > 0 whose prerequisites are fully satisfied.
3. Compute priority score for each eligible topic based on exam urgency, difficulty, importance, and remaining hours.
4. Push eligible topics into the custom Max Heap Priority Queue.
5. Iteratively pop the highest-priority topic.
6. Allocate study time (up to max_session_duration, daily_remaining_hours, or topic's remaining hours).
7. Update topic's remaining hours. If remaining hours reach 0, mark as completed.
8. Dynamically unlock dependent topics whose prerequisites are now satisfied and insert them into the Priority Queue.
9. If the current topic still has remaining hours > 0, recompute priority and re-insert into the Priority Queue.
10. Repeat until available daily study hours are exhausted or priority queue is empty.
"""

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
import copy

from .models import Topic, StudySession
from .priority import calculate_priority_score
from .priority_queue import PriorityQueue
from .graph import DependencyGraph, CircularDependencyError


class GreedyScheduler:
    """
    Greedy study slot scheduler leveraging custom Priority Queue (Max Heap) and Dependency Graph.
    """

    def __init__(
        self,
        max_session_duration: float = 1.5,
        default_start_time: str = "09:00",
        break_duration_minutes: int = 15,
        strict_prerequisites: bool = False
    ):
        self.max_session_duration = max_session_duration
        self.default_start_time = default_start_time
        self.break_duration_minutes = break_duration_minutes
        self.strict_prerequisites = strict_prerequisites

    @staticmethod
    def _parse_time_to_minutes(time_str: str) -> int:
        """Converts HH:MM string to total minutes from midnight."""
        parts = time_str.split(":")
        hours = int(parts[0])
        minutes = int(parts[1]) if len(parts) > 1 else 0
        return hours * 60 + minutes

    @staticmethod
    def _format_minutes_to_time(total_minutes: int) -> str:
        """Converts total minutes from midnight to HH:MM string."""
        hours = (total_minutes // 60) % 24
        mins = total_minutes % 60
        return f"{hours:02d}:{mins:02d}"

    @staticmethod
    def _is_prereq_satisfied(topic: Topic, completed_identifiers: Set[Any]) -> bool:
        """
        Returns True if all prerequisite IDs/names for the topic are present in completed_identifiers.
        """
        if not topic.prerequisites:
            return True
        return all(p in completed_identifiers for p in topic.prerequisites)

    def generate_daily_schedule(
        self,
        topics: List[Topic],
        daily_available_hours: float,
        target_date: Optional[date] = None,
        start_time_str: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates an optimized daily schedule using Greedy + Priority Queue strategy with dynamic prerequisite checking.

        Returns a dictionary containing:
        - "sessions": List[StudySession]
        - "total_hours_scheduled": float
        - "remaining_day_hours": float
        - "updated_topics": List[Topic]
        - "topological_order": List[Any]
        - "warnings": List[str]
        - "has_cycle": bool
        """
        if target_date is None:
            target_date = date.today()

        if start_time_str is None:
            start_time_str = self.default_start_time

        target_date_str = target_date.strftime("%Y-%m-%d")
        current_minutes = self._parse_time_to_minutes(start_time_str)

        # Deep copy topics to avoid unintended side effects during trial schedules
        working_topics = [copy.deepcopy(t) for t in topics]

        # Step 1: Graph Validation & Topological Sorting
        graph, warnings = DependencyGraph.build_from_topics(working_topics)
        topological_order: List[Any] = []
        has_cycle = False

        try:
            topological_order = graph.topological_sort()
        except CircularDependencyError as cycle_err:
            has_cycle = True
            warning_msg = f"Circular dependency detected: {cycle_err}"
            warnings.append(warning_msg)
            if self.strict_prerequisites:
                raise cycle_err

        # Track completed topic identifiers (both ID and name if available)
        completed_identifiers: Set[Any] = set()
        for t in working_topics:
            if t.completed or t.remaining_hours <= 0:
                if t.id is not None:
                    completed_identifiers.add(t.id)
                if t.name:
                    completed_identifiers.add(t.name)

        # Track topics already enqueued into Priority Queue to prevent duplicate pushes
        queued_identifiers: Set[Any] = set()

        pq = PriorityQueue[Topic]()

        # Helper closure to push newly eligible topics into the PQ
        def enqueue_eligible_topics():
            for topic in working_topics:
                t_identifier = topic.id if topic.id is not None else topic.name
                if (
                    t_identifier not in queued_identifiers
                    and not topic.completed
                    and topic.remaining_hours > 0
                    and self._is_prereq_satisfied(topic, completed_identifiers)
                ):
                    score = calculate_priority_score(topic, target_date)
                    pq.insert(score, topic)
                    queued_identifiers.add(t_identifier)

        # Initial Enqueue
        enqueue_eligible_topics()

        scheduled_sessions: List[StudySession] = []
        allocated_hours = 0.0

        # Step 2: Greedy Allocation Loop
        while allocated_hours < daily_available_hours and not pq.is_empty():
            remaining_day_hours = daily_available_hours - allocated_hours
            priority_score, top_topic = pq.pop()

            # Determine duration for this study session
            session_hours = min(
                self.max_session_duration,
                top_topic.remaining_hours,
                remaining_day_hours
            )
            session_hours = round(session_hours, 2)

            if session_hours <= 0:
                break

            # Calculate start and end times
            session_duration_mins = int(round(session_hours * 60))
            start_str = self._format_minutes_to_time(current_minutes)
            end_minutes = current_minutes + session_duration_mins
            end_str = self._format_minutes_to_time(end_minutes)

            # Record session
            session = StudySession(
                topic_id=top_topic.id,
                topic_name=top_topic.name,
                subject_name=top_topic.subject_name,
                date=target_date_str,
                start_time=start_str,
                end_time=end_str,
                duration_hours=session_hours,
                priority_score=priority_score,
                completed=False
            )
            scheduled_sessions.append(session)

            # Update topic state & scheduler state
            top_topic.remaining_hours = round(top_topic.remaining_hours - session_hours, 2)
            if top_topic.remaining_hours <= 0.001:
                top_topic.remaining_hours = 0.0
                top_topic.completed = True
                if top_topic.id is not None:
                    completed_identifiers.add(top_topic.id)
                if top_topic.name:
                    completed_identifiers.add(top_topic.name)

            allocated_hours = round(allocated_hours + session_hours, 2)
            current_minutes = end_minutes + self.break_duration_minutes

            # Dynamically unlock any newly eligible dependent topics whose prerequisites are now complete
            enqueue_eligible_topics()

            # Re-insert current topic into Priority Queue if it still has work remaining
            if top_topic.remaining_hours > 0:
                new_score = calculate_priority_score(top_topic, target_date)
                pq.insert(new_score, top_topic)

        remaining_day_hours = round(max(0.0, daily_available_hours - allocated_hours), 2)

        return {
            "sessions": scheduled_sessions,
            "total_hours_scheduled": allocated_hours,
            "remaining_day_hours": remaining_day_hours,
            "updated_topics": working_topics,
            "topological_order": topological_order,
            "warnings": warnings,
            "has_cycle": has_cycle
        }
