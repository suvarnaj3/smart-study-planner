"""
services/planner_service.py
Service layer connecting Flask API handlers to DatabaseManager and DSA algorithms.

Encapsulates business logic, domain validation, data serialization, and integration between:
- SQLite persistence layer (database/db.py)
- Dynamic Greedy Max-Heap Scheduler (dsa/scheduler.py)
- Dependency Graph & Topological Sort (dsa/graph.py)
"""

from datetime import date, datetime
from typing import Dict, List, Optional, Any, Union
from database.db import DatabaseManager
from dsa.models import Subject, Topic, Exam, StudySession
from dsa.scheduler import GreedyScheduler


class PlannerService:
    """
    Application Service orchestrating data persistence, business rules, and DSA scheduling.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        if db_manager is None:
            db_manager = DatabaseManager("planner.db")
        self.db = db_manager

    # -------------------------------------------------------------------------
    # SERIALIZATION HELPERS
    # -------------------------------------------------------------------------

    @staticmethod
    def _subject_to_dict(subject: Subject) -> Dict[str, Any]:
        return {
            "id": subject.id,
            "name": subject.name
        }

    @staticmethod
    def _topic_to_dict(topic: Topic) -> Dict[str, Any]:
        return {
            "id": topic.id,
            "subject_id": topic.subject_id,
            "subject_name": topic.subject_name,
            "name": topic.name,
            "difficulty": topic.difficulty,
            "estimated_hours": topic.estimated_hours,
            "remaining_hours": topic.remaining_hours,
            "importance": topic.importance,
            "exam_date": topic.exam_date if isinstance(topic.exam_date, str) else (topic.exam_date.strftime("%Y-%m-%d") if topic.exam_date else None),
            "completed": topic.completed,
            "prerequisites": topic.prerequisites
        }

    @staticmethod
    def _exam_to_dict(exam: Exam) -> Dict[str, Any]:
        return {
            "id": exam.id,
            "subject_id": exam.subject_id,
            "subject_name": exam.subject_name,
            "exam_date": exam.exam_date if isinstance(exam.exam_date, str) else exam.exam_date.strftime("%Y-%m-%d")
        }

    @staticmethod
    def _session_to_dict(session: StudySession) -> Dict[str, Any]:
        return {
            "id": session.id,
            "topic_id": session.topic_id,
            "topic_name": session.topic_name,
            "subject_name": session.subject_name,
            "date": session.date,
            "start_time": session.start_time,
            "end_time": session.end_time,
            "duration_hours": session.duration_hours,
            "priority_score": session.priority_score,
            "completed": session.completed
        }

    # -------------------------------------------------------------------------
    # SUBJECT SERVICES
    # -------------------------------------------------------------------------

    def get_all_subjects(self) -> List[Dict[str, Any]]:
        subjects = self.db.get_subjects()
        return [self._subject_to_dict(s) for s in subjects]

    def create_subject(self, name: str) -> Dict[str, Any]:
        if not name or not isinstance(name, str) or not name.strip():
            raise ValueError("Subject name is required and cannot be blank.")
        name = name.strip()
        subject_id = self.db.add_subject(name)
        return {"id": subject_id, "name": name}

    def delete_subject(self, subject_id: int) -> bool:
        subject = self.db.get_subject_by_id(subject_id)
        if not subject:
            return False
        return self.db.delete_subject(subject_id)

    # -------------------------------------------------------------------------
    # TOPIC SERVICES
    # -------------------------------------------------------------------------

    def get_all_topics(self, subject_id: Optional[int] = None) -> List[Dict[str, Any]]:
        topics = self.db.get_topics(subject_id=subject_id)
        return [self._topic_to_dict(t) for t in topics]

    def get_topic_by_id(self, topic_id: int) -> Optional[Dict[str, Any]]:
        topic = self.db.get_topic_by_id(topic_id)
        if not topic:
            return None
        return self._topic_to_dict(topic)

    def create_topic(
        self,
        subject_id: int,
        name: str,
        difficulty: int = 3,
        estimated_hours: float = 1.0,
        importance: int = 3,
        exam_date: Optional[str] = None,
        remaining_hours: Optional[float] = None,
        prerequisites: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        # Domain validations
        subject = self.db.get_subject_by_id(subject_id)
        if not subject:
            raise ValueError(f"Subject with ID {subject_id} does not exist.")

        if not name or not isinstance(name, str) or not name.strip():
            raise ValueError("Topic name is required and cannot be blank.")

        if not isinstance(difficulty, int) or not (1 <= difficulty <= 5):
            raise ValueError("Difficulty must be an integer between 1 and 5.")

        if not isinstance(importance, int) or not (1 <= importance <= 5):
            raise ValueError("Importance must be an integer between 1 and 5.")

        if not isinstance(estimated_hours, (int, float)) or estimated_hours < 0:
            raise ValueError("Estimated hours must be a non-negative number.")

        if remaining_hours is not None:
            if not isinstance(remaining_hours, (int, float)) or remaining_hours < 0:
                raise ValueError("Remaining hours must be a non-negative number.")
        else:
            remaining_hours = float(estimated_hours)

        if exam_date:
            try:
                datetime.strptime(exam_date, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Exam date must be in YYYY-MM-DD format.")

        # Validate prerequisite topic IDs exist
        if prerequisites:
            for p_id in prerequisites:
                prereq_topic = self.db.get_topic_by_id(p_id)
                if not prereq_topic:
                    raise ValueError(f"Prerequisite topic ID {p_id} does not exist.")

        topic_id = self.db.add_topic(
            subject_id=subject_id,
            name=name.strip(),
            difficulty=difficulty,
            estimated_hours=float(estimated_hours),
            importance=importance,
            exam_date=exam_date,
            remaining_hours=float(remaining_hours),
            prerequisites=prerequisites
        )

        topic = self.db.get_topic_by_id(topic_id)
        return self._topic_to_dict(topic)

    def delete_topic(self, topic_id: int) -> bool:
        topic = self.db.get_topic_by_id(topic_id)
        if not topic:
            return False
        return self.db.delete_topic(topic_id)

    # -------------------------------------------------------------------------
    # PREREQUISITE SERVICES
    # -------------------------------------------------------------------------

    def add_prerequisite(self, topic_id: int, prerequisite_topic_id: int) -> Dict[str, Any]:
        if topic_id == prerequisite_topic_id:
            raise ValueError("A topic cannot be a prerequisite of itself.")

        topic = self.db.get_topic_by_id(topic_id)
        if not topic:
            raise ValueError(f"Topic ID {topic_id} does not exist.")

        prereq = self.db.get_topic_by_id(prerequisite_topic_id)
        if not prereq:
            raise ValueError(f"Prerequisite topic ID {prerequisite_topic_id} does not exist.")

        self.db.add_prerequisite(topic_id, prerequisite_topic_id)
        updated_topic = self.db.get_topic_by_id(topic_id)
        return self._topic_to_dict(updated_topic)

    def remove_prerequisite(self, topic_id: int, prerequisite_topic_id: int) -> bool:
        return self.db.remove_prerequisite(topic_id, prerequisite_topic_id)

    # -------------------------------------------------------------------------
    # EXAM SERVICES
    # -------------------------------------------------------------------------

    def get_all_exams(self, subject_id: Optional[int] = None) -> List[Dict[str, Any]]:
        exams = self.db.get_exams(subject_id=subject_id)
        return [self._exam_to_dict(e) for e in exams]

    def create_exam(self, subject_id: int, exam_date: str) -> Dict[str, Any]:
        subject = self.db.get_subject_by_id(subject_id)
        if not subject:
            raise ValueError(f"Subject with ID {subject_id} does not exist.")

        try:
            datetime.strptime(exam_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Exam date must be in YYYY-MM-DD format.")

        exam_id = self.db.add_exam(subject_id, exam_date)
        return {
            "id": exam_id,
            "subject_id": subject_id,
            "subject_name": subject.name,
            "exam_date": exam_date
        }

    # -------------------------------------------------------------------------
    # SCHEDULER & SESSION SERVICES
    # -------------------------------------------------------------------------

    def generate_schedule(
        self,
        daily_available_hours: float,
        target_date_str: Optional[str] = None,
        max_session_duration: float = 1.5,
        start_time_str: str = "09:00"
    ) -> Dict[str, Any]:
        if not isinstance(daily_available_hours, (int, float)) or daily_available_hours < 0:
            raise ValueError("Daily available hours must be a non-negative number.")

        target_date = date.today()
        if target_date_str:
            try:
                target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("Target date must be in YYYY-MM-DD format.")

        # Retrieve topics from SQLite database
        topics = self.db.get_topics()

        # Run Greedy Scheduler (which invokes DependencyGraph + MaxHeap internally)
        scheduler = GreedyScheduler(
            max_session_duration=float(max_session_duration),
            default_start_time=start_time_str
        )
        result = scheduler.generate_daily_schedule(
            topics=topics,
            daily_available_hours=float(daily_available_hours),
            target_date=target_date
        )

        # Persist generated sessions to DB
        generated_sessions = result["sessions"]
        saved_session_ids = self.db.save_study_sessions(generated_sessions)

        # Update session IDs in response objects
        session_dicts: List[Dict[str, Any]] = []
        for idx, session in enumerate(generated_sessions):
            if idx < len(saved_session_ids):
                session.id = saved_session_ids[idx]
            session_dicts.append(self._session_to_dict(session))

        return {
            "sessions": session_dicts,
            "total_hours_scheduled": result["total_hours_scheduled"],
            "remaining_day_hours": result["remaining_day_hours"],
            "topological_order": result["topological_order"],
            "warnings": result["warnings"],
            "has_cycle": result["has_cycle"]
        }

    def get_study_sessions(self, date_str: Optional[str] = None) -> List[Dict[str, Any]]:
        if date_str:
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Date filter must be in YYYY-MM-DD format.")

        sessions = self.db.get_study_sessions(date_str=date_str)
        return [self._session_to_dict(s) for s in sessions]

    def update_topic_progress(
        self,
        topic_id: int,
        remaining_hours: Optional[float] = None,
        completed: Optional[bool] = None
    ) -> Dict[str, Any]:
        topic = self.db.get_topic_by_id(topic_id)
        if not topic:
            raise ValueError(f"Topic with ID {topic_id} does not exist.")

        new_remaining = topic.remaining_hours if remaining_hours is None else float(remaining_hours)
        if new_remaining < 0:
            raise ValueError("Remaining hours cannot be negative.")

        new_completed = topic.completed if completed is None else bool(completed)
        if new_remaining <= 0:
            new_completed = True

        self.db.update_topic_progress(topic_id, new_remaining, new_completed)
        updated_topic = self.db.get_topic_by_id(topic_id)
        return self._topic_to_dict(updated_topic)

    def update_session_completion(self, session_id: int, completed: bool) -> bool:
        return self.db.update_session_completion(session_id, completed)
