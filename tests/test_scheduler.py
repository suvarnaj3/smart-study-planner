"""
tests/test_scheduler.py
Unit tests for Greedy Study Slot Scheduler.
"""

from datetime import date
from dsa.models import Topic
from dsa.scheduler import GreedyScheduler


def test_normal_scheduling():
    scheduler = GreedyScheduler(max_session_duration=1.5, default_start_time="09:00", break_duration_minutes=15)
    today = date(2026, 9, 22)

    topics = [
        Topic(id=1, subject_name="DSA", name="Graphs", difficulty=5, importance=5, estimated_hours=6.0, remaining_hours=6.0, exam_date="2026-09-24"),
        Topic(id=2, subject_name="DSA", name="Trees", difficulty=4, importance=4, estimated_hours=3.0, remaining_hours=3.0, exam_date="2026-09-26"),
        Topic(id=3, subject_name="DBMS", name="SQL", difficulty=2, importance=3, estimated_hours=2.0, remaining_hours=2.0, exam_date="2026-10-05"),
    ]

    # Run scheduler with 4 available hours
    result = scheduler.generate_daily_schedule(topics, daily_available_hours=4.0, target_date=today)

    sessions = result["sessions"]
    assert len(sessions) > 0
    assert result["total_hours_scheduled"] == 4.0
    assert result["remaining_day_hours"] == 0.0

    # Verify highest priority topic (Graphs) was scheduled first
    assert sessions[0].topic_name == "Graphs"
    assert sessions[0].start_time == "09:00"
    assert sessions[0].end_time == "10:30"
    assert sessions[0].duration_hours == 1.5

    # Verify second session starts after 15 min break (10:45)
    assert sessions[1].start_time == "10:45"
    assert sessions[1].end_time == "12:15"


def test_incomplete_prerequisite_prevents_scheduling():
    """
    Verifies that a topic with an incomplete prerequisite is NOT enqueued or scheduled,
    even if it has maximum difficulty and importance ratings.
    Catches bugs where high-priority dependent topics bypass prerequisite gates.
    """
    scheduler = GreedyScheduler()
    today = date(2026, 9, 22)

    prereq_topic = Topic(id=1, name="Arrays", completed=False, remaining_hours=2.0)
    dependent_topic = Topic(
        id=2, name="Trees", completed=False, remaining_hours=2.0, prerequisites=[1], difficulty=5, importance=5
    )

    result = scheduler.generate_daily_schedule([prereq_topic, dependent_topic], daily_available_hours=2.0, target_date=today)
    scheduled_names = [s.topic_name for s in result["sessions"]]

    assert "Arrays" in scheduled_names
    assert "Trees" not in scheduled_names


def test_completed_prerequisite_allows_scheduling():
    """
    Verifies that when a prerequisite topic is already completed, the dependent topic enters the queue normally.
    Catches bugs where prerequisite locks remain permanently active.
    """
    scheduler = GreedyScheduler()
    today = date(2026, 9, 22)

    completed_prereq = Topic(id=1, name="Arrays", completed=True, remaining_hours=0.0)
    dependent_topic = Topic(id=2, name="Trees", completed=False, remaining_hours=2.0, prerequisites=[1])

    result = scheduler.generate_daily_schedule([completed_prereq, dependent_topic], daily_available_hours=2.0, target_date=today)
    scheduled_names = [s.topic_name for s in result["sessions"]]

    assert "Trees" in scheduled_names


def test_dynamic_prerequisite_unlocking_during_session():
    """
    Verifies dynamic prerequisite resolution: when a prerequisite topic finishes its remaining study hours
    during the day's schedule execution, dependent topics become eligible and get scheduled in subsequent slots.
    Catches static enqueue bugs where prerequisites finished mid-day fail to unlock dependent topics.
    """
    scheduler = GreedyScheduler(max_session_duration=1.0)
    today = date(2026, 9, 22)

    prereq_topic = Topic(id=1, name="Arrays", completed=False, remaining_hours=1.0)
    dependent_topic = Topic(id=2, name="Searching", completed=False, remaining_hours=2.0, prerequisites=[1])

    # Available daily time = 3.0 hours. Arrays needs 1.0 hour. Searching needs 2.0 hours.
    result = scheduler.generate_daily_schedule([prereq_topic, dependent_topic], daily_available_hours=3.0, target_date=today)
    scheduled_names = [s.topic_name for s in result["sessions"]]

    # Slot 1 (09:00 - 10:00): Arrays (finishes remaining 1.0h -> completed!)
    # Slot 2 & 3: Searching (unlocked dynamically after Arrays completes!)
    assert scheduled_names == ["Arrays", "Searching", "Searching"]
    assert result["total_hours_scheduled"] == 3.0


def test_circular_dependency_safety():
    """
    Verifies that circular dependencies (Topic A -> Topic B -> Topic A) do not cause an infinite loop,
    stack overflow, or invalid scheduling.
    Catches infinite loop crashes in dependency resolution and scheduler loops.
    """
    scheduler = GreedyScheduler()
    today = date(2026, 9, 22)

    topic_a = Topic(id=1, name="Topic A", completed=False, remaining_hours=2.0, prerequisites=[2])
    topic_b = Topic(id=2, name="Topic B", completed=False, remaining_hours=2.0, prerequisites=[1])

    result = scheduler.generate_daily_schedule([topic_a, topic_b], daily_available_hours=4.0, target_date=today)

    # Neither topic can be scheduled because neither prerequisite is completed
    assert len(result["sessions"]) == 0
    assert result["total_hours_scheduled"] == 0.0
    assert result["remaining_day_hours"] == 4.0


def test_topic_requiring_multiple_sessions():
    scheduler = GreedyScheduler(max_session_duration=1.5, default_start_time="09:00", break_duration_minutes=15)
    today = date(2026, 9, 22)

    topics = [
        Topic(id=10, subject_name="DSA", name="Graph Traversal", difficulty=5, importance=5, estimated_hours=6.0, remaining_hours=6.0, exam_date="2026-09-23")
    ]

    result = scheduler.generate_daily_schedule(topics, daily_available_hours=4.0, target_date=today)

    sessions = result["sessions"]
    assert len(sessions) == 3
    assert result["total_hours_scheduled"] == 4.0

    durations = [s.duration_hours for s in sessions]
    assert durations == [1.5, 1.5, 1.0]

    updated_topic = [t for t in result["updated_topics"] if t.id == 10][0]
    assert updated_topic.remaining_hours == 2.0


def test_no_available_study_time():
    scheduler = GreedyScheduler()
    today = date(2026, 9, 22)

    topics = [
        Topic(id=1, name="Arrays", remaining_hours=2.0)
    ]

    result = scheduler.generate_daily_schedule(topics, daily_available_hours=0.0, target_date=today)
    assert len(result["sessions"]) == 0
    assert result["total_hours_scheduled"] == 0.0
    assert result["remaining_day_hours"] == 0.0


def test_completed_topics_excluded():
    scheduler = GreedyScheduler()
    today = date(2026, 9, 22)

    topics = [
        Topic(id=1, name="Completed Topic", remaining_hours=0.0, completed=True),
        Topic(id=2, name="Active Topic", remaining_hours=2.0, completed=False)
    ]

    result = scheduler.generate_daily_schedule(topics, daily_available_hours=3.0, target_date=today)
    sessions = result["sessions"]
    assert len(sessions) == 2  # 1.5h + 0.5h for Active Topic
    for s in sessions:
        assert s.topic_name == "Active Topic"


def test_more_work_than_available_time():
    scheduler = GreedyScheduler(max_session_duration=2.0)
    today = date(2026, 9, 22)

    topics = [
        Topic(id=1, name="Topic 1", difficulty=5, importance=5, estimated_hours=5.0, remaining_hours=5.0, exam_date="2026-09-23"),
        Topic(id=2, name="Topic 2", difficulty=4, importance=4, estimated_hours=5.0, remaining_hours=5.0, exam_date="2026-09-24"),
    ]

    result = scheduler.generate_daily_schedule(topics, daily_available_hours=3.0, target_date=today)
    assert result["total_hours_scheduled"] == 3.0
    assert result["remaining_day_hours"] == 0.0
