"""
tests/test_priority.py
Unit tests for Priority Score and Exam Urgency engine.
"""

from datetime import date, timedelta
from dsa.models import Topic
from dsa.priority import calculate_priority_score, calculate_exam_urgency


def test_exam_urgency_date_diffs():
    today = date(2026, 9, 22)

    # Exam today or overdue
    assert calculate_exam_urgency("2026-09-22", today) == 100.0
    assert calculate_exam_urgency("2026-09-20", today) == 100.0

    # Exam tomorrow
    assert calculate_exam_urgency("2026-09-23", today) == 95.0

    # Exam in 3 days
    assert calculate_exam_urgency("2026-09-25", today) == 85.0

    # Exam in 30 days
    assert calculate_exam_urgency("2026-10-22", today) == 35.0

    # No exam date
    assert calculate_exam_urgency(None, today) == 20.0


def test_higher_exam_urgency_increases_priority():
    """
    Verifies that a topic with a closer exam date receives a strictly higher priority score.
    Catches off-by-one errors in date parsing and inverted date calculation formulas.
    """
    today = date(2026, 9, 22)

    topic_urgent = Topic(
        name="Urgent Exam Topic",
        difficulty=3,
        importance=3,
        estimated_hours=4.0,
        remaining_hours=4.0,
        exam_date="2026-09-23"  # Tomorrow
    )

    topic_distant = Topic(
        name="Distant Exam Topic",
        difficulty=3,
        importance=3,
        estimated_hours=4.0,
        remaining_hours=4.0,
        exam_date="2026-10-30"  # Far away
    )

    score_urgent = calculate_priority_score(topic_urgent, today)
    score_distant = calculate_priority_score(topic_distant, today)

    assert score_urgent > score_distant


def test_higher_difficulty_increases_priority():
    """
    Verifies that a topic with higher difficulty (1-5 scale) receives a higher priority score.
    Catches bugs where difficulty rating is ignored, unweighted, or subtracted instead of added.
    """
    today = date(2026, 9, 22)

    hard_topic = Topic(name="Hard Topic", difficulty=5, importance=3, remaining_hours=2.0, exam_date="2026-10-01")
    easy_topic = Topic(name="Easy Topic", difficulty=1, importance=3, remaining_hours=2.0, exam_date="2026-10-01")

    assert calculate_priority_score(hard_topic, today) > calculate_priority_score(easy_topic, today)


def test_higher_importance_increases_priority():
    """
    Verifies that a topic with higher importance rating (1-5 scale) receives a higher priority score.
    Catches bugs where importance scale is defaulted to a constant or overridden by difficulty.
    """
    today = date(2026, 9, 22)

    vital_topic = Topic(name="Vital Topic", difficulty=3, importance=5, remaining_hours=2.0, exam_date="2026-10-01")
    minor_topic = Topic(name="Minor Topic", difficulty=3, importance=1, remaining_hours=2.0, exam_date="2026-10-01")

    assert calculate_priority_score(vital_topic, today) > calculate_priority_score(minor_topic, today)


def test_completed_or_zero_hours():
    today = date(2026, 9, 22)

    topic_completed = Topic(
        name="Finished Topic",
        difficulty=5,
        importance=5,
        remaining_hours=0.0,
        completed=True
    )

    assert calculate_priority_score(topic_completed, today) == 0.0

    topic_zero_hours = Topic(
        name="No Remaining Hours Topic",
        difficulty=5,
        importance=5,
        remaining_hours=0.0,
        completed=False
    )

    assert calculate_priority_score(topic_zero_hours, today) == 0.0
