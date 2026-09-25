"""
dsa/priority.py
Priority calculation engine for Smart Study Planner topics.

Calculates dynamic priority score based on:
1. Exam urgency (days remaining until exam date)
2. Difficulty rating (1-5)
3. Importance rating (1-5)
4. Remaining study hours vs estimated hours
"""

from datetime import date, datetime
from typing import Optional, Union
from .models import Topic


def calculate_exam_urgency(exam_date: Optional[Union[str, date]], target_date: Optional[date] = None) -> float:
    """
    Calculate exam urgency score on a 10 - 100 scale.
    Higher score indicates higher urgency (exam is sooner).
    """
    if not exam_date:
        return 20.0  # Baseline urgency if no exam date is set

    if target_date is None:
        target_date = date.today()

    exam_date_obj: Optional[date] = None
    if isinstance(exam_date, date):
        exam_date_obj = exam_date
    elif isinstance(exam_date, str):
        try:
            exam_date_obj = datetime.strptime(exam_date, "%Y-%m-%d").date()
        except ValueError:
            return 20.0

    if not exam_date_obj:
        return 20.0

    days_left = (exam_date_obj - target_date).days

    if days_left <= 0:
        return 100.0  # Overdue or today
    elif days_left == 1:
        return 95.0
    elif days_left <= 3:
        return 85.0
    elif days_left <= 7:
        return 70.0
    elif days_left <= 14:
        return 50.0
    elif days_left <= 30:
        return 35.0
    else:
        # Gradually decrease for exams far in the future
        return max(10.0, 100.0 - (days_left * 2.0))


def calculate_priority_score(
    topic: Topic,
    target_date: Optional[date] = None,
    urgency_weight: float = 1.0,
    difficulty_weight: float = 10.0,
    importance_weight: float = 12.0,
    remaining_weight: float = 4.0
) -> float:
    """
    Computes a overall priority score for a topic.
    Returns 0.0 if topic is completed or has no remaining study hours.
    
    Formula:
    priority_score = (urgency * urgency_weight) +
                     (difficulty * difficulty_weight) +
                     (importance * importance_weight) +
                     (remaining_hours * remaining_weight)
    """
    if topic.completed or topic.remaining_hours <= 0:
        return 0.0

    urgency = calculate_exam_urgency(topic.exam_date, target_date)
    difficulty_score = float(topic.difficulty) * difficulty_weight
    importance_score = float(topic.importance) * importance_weight
    remaining_score = float(topic.remaining_hours) * remaining_weight

    score = (urgency * urgency_weight) + difficulty_score + importance_score + remaining_score
    return round(score, 2)
