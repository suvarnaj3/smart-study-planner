"""
dsa/models.py
Data structures representing Subject, Topic, Exam, and StudySession entities.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional, Union


@dataclass
class Subject:
    id: Optional[int] = None
    name: str = ""


@dataclass
class Topic:
    id: Optional[int] = None
    subject_id: Optional[int] = None
    subject_name: str = ""
    name: str = ""
    difficulty: int = 3          # Scale 1-5
    estimated_hours: float = 1.0
    remaining_hours: float = 1.0
    importance: int = 3          # Scale 1-5
    exam_date: Optional[Union[str, date]] = None
    completed: bool = False
    prerequisites: List[int] = field(default_factory=list)

    def get_exam_date_obj(self) -> Optional[date]:
        if not self.exam_date:
            return None
        if isinstance(self.exam_date, date):
            return self.exam_date
        if isinstance(self.exam_date, str):
            try:
                return datetime.strptime(self.exam_date, "%Y-%m-%d").date()
            except ValueError:
                return None
        return None


@dataclass
class Exam:
    id: Optional[int] = None
    subject_id: Optional[int] = None
    subject_name: str = ""
    exam_date: Union[str, date] = ""


@dataclass
class StudySession:
    id: Optional[int] = None
    topic_id: Optional[int] = None
    topic_name: str = ""
    subject_name: str = ""
    date: str = ""                # YYYY-MM-DD
    start_time: str = ""          # HH:MM
    end_time: str = ""            # HH:MM
    duration_hours: float = 0.0
    priority_score: float = 0.0
    completed: bool = False
