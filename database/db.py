"""
database/db.py
SQLite Data Access Layer for Smart Study Planner.

Provides persistence and CRUD operations for Subjects, Topics, Exams, Dependencies, and Study Sessions.
Converts database rows to/from domain dataclasses (Topic, Subject, Exam, StudySession).
Enforces foreign keys using `PRAGMA foreign_keys = ON;`.
"""

import os
import sqlite3
from typing import Dict, List, Optional, Tuple, Any, Union
from dsa.models import Subject, Topic, Exam, StudySession


def get_connection(db_path: str = "planner.db") -> sqlite3.Connection:
    """
    Creates and returns a SQLite connection with foreign key enforcement and Row factory.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: str = "planner.db", schema_path: Optional[str] = None) -> None:
    """
    Initializes database tables using the schema.sql file.
    """
    if schema_path is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        schema_path = os.path.join(base_dir, "schema.sql")

    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    conn = get_connection(db_path)
    try:
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()


class DatabaseManager:
    """
    Encapsulates database persistence logic and CRUD functions for Smart Study Planner.
    """

    def __init__(self, db_path: str = "planner.db"):
        self.db_path = db_path

    def get_conn(self) -> sqlite3.Connection:
        return get_connection(self.db_path)

    # -------------------------------------------------------------------------
    # SUBJECT CRUD
    # -------------------------------------------------------------------------

    def add_subject(self, name: str) -> int:
        """Adds a new subject. Returns the generated subject ID."""
        name = name.strip()
        if not name:
            raise ValueError("Subject name cannot be empty.")

        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO subjects (name) VALUES (?)", (name,))
            conn.commit()
            return cursor.lastrowid

    def get_subjects(self) -> List[Subject]:
        """Retrieves all subjects."""
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM subjects ORDER BY name ASC")
            rows = cursor.fetchall()
            return [Subject(id=r["id"], name=r["name"]) for r in rows]

    def get_subject_by_id(self, subject_id: int) -> Optional[Subject]:
        """Retrieves a single subject by ID."""
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM subjects WHERE id = ?", (subject_id,))
            row = cursor.fetchone()
            if row:
                return Subject(id=row["id"], name=row["name"])
            return None

    def delete_subject(self, subject_id: int) -> bool:
        """Deletes a subject by ID. Cascades deletion to associated topics, exams, sessions."""
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
            conn.commit()
            return cursor.rowcount > 0

    # -------------------------------------------------------------------------
    # TOPIC CRUD
    # -------------------------------------------------------------------------

    def add_topic(
        self,
        subject_id: int,
        name: str,
        difficulty: int = 3,
        estimated_hours: float = 1.0,
        importance: int = 3,
        exam_date: Optional[str] = None,
        remaining_hours: Optional[float] = None,
        completed: bool = False,
        prerequisites: Optional[List[int]] = None
    ) -> int:
        """Adds a new topic under a subject. Optionally links prerequisite topic IDs."""
        name = name.strip()
        if not name:
            raise ValueError("Topic name cannot be empty.")
        if not (1 <= difficulty <= 5):
            raise ValueError("Difficulty must be between 1 and 5.")
        if not (1 <= importance <= 5):
            raise ValueError("Importance must be between 1 and 5.")
        if estimated_hours < 0:
            raise ValueError("Estimated hours cannot be negative.")

        if remaining_hours is None:
            remaining_hours = estimated_hours

        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO topics (subject_id, name, difficulty, estimated_hours, remaining_hours, importance, exam_date, completed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (subject_id, name, difficulty, estimated_hours, remaining_hours, importance, exam_date, 1 if completed else 0)
            )
            topic_id = cursor.lastrowid

            if prerequisites:
                for prereq_id in prerequisites:
                    cursor.execute(
                        "INSERT INTO dependencies (topic_id, prerequisite_topic_id) VALUES (?, ?)",
                        (topic_id, prereq_id)
                    )

            conn.commit()
            return topic_id

    def get_topics(self, subject_id: Optional[int] = None) -> List[Topic]:
        """Retrieves topics (optionally filtered by subject) with subject names and prerequisite IDs populated."""
        with self.get_conn() as conn:
            cursor = conn.cursor()
            if subject_id is not None:
                cursor.execute(
                    """
                    SELECT t.id, t.subject_id, s.name as subject_name, t.name, t.difficulty,
                           t.estimated_hours, t.remaining_hours, t.importance, t.exam_date, t.completed
                    FROM topics t
                    JOIN subjects s ON t.subject_id = s.id
                    WHERE t.subject_id = ?
                    ORDER BY t.id ASC
                    """,
                    (subject_id,)
                )
            else:
                cursor.execute(
                    """
                    SELECT t.id, t.subject_id, s.name as subject_name, t.name, t.difficulty,
                           t.estimated_hours, t.remaining_hours, t.importance, t.exam_date, t.completed
                    FROM topics t
                    JOIN subjects s ON t.subject_id = s.id
                    ORDER BY t.id ASC
                    """
                )
            rows = cursor.fetchall()

            topics: List[Topic] = []
            for r in rows:
                t_id = r["id"]
                # Fetch prerequisite IDs for topic
                cursor.execute("SELECT prerequisite_topic_id FROM dependencies WHERE topic_id = ?", (t_id,))
                prereq_rows = cursor.fetchall()
                prereqs = [p["prerequisite_topic_id"] for p in prereq_rows]

                topic = Topic(
                    id=t_id,
                    subject_id=r["subject_id"],
                    subject_name=r["subject_name"],
                    name=r["name"],
                    difficulty=r["difficulty"],
                    estimated_hours=r["estimated_hours"],
                    remaining_hours=r["remaining_hours"],
                    importance=r["importance"],
                    exam_date=r["exam_date"],
                    completed=bool(r["completed"]),
                    prerequisites=prereqs
                )
                topics.append(topic)

            return topics

    def get_topic_by_id(self, topic_id: int) -> Optional[Topic]:
        """Retrieves a single topic by ID."""
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT t.id, t.subject_id, s.name as subject_name, t.name, t.difficulty,
                       t.estimated_hours, t.remaining_hours, t.importance, t.exam_date, t.completed
                FROM topics t
                JOIN subjects s ON t.subject_id = s.id
                WHERE t.id = ?
                """,
                (topic_id,)
            )
            r = cursor.fetchone()
            if not r:
                return None

            cursor.execute("SELECT prerequisite_topic_id FROM dependencies WHERE topic_id = ?", (topic_id,))
            prereqs = [p["prerequisite_topic_id"] for p in cursor.fetchall()]

            return Topic(
                id=r["id"],
                subject_id=r["subject_id"],
                subject_name=r["subject_name"],
                name=r["name"],
                difficulty=r["difficulty"],
                estimated_hours=r["estimated_hours"],
                remaining_hours=r["remaining_hours"],
                importance=r["importance"],
                exam_date=r["exam_date"],
                completed=bool(r["completed"]),
                prerequisites=prereqs
            )

    def update_topic_progress(self, topic_id: int, remaining_hours: float, completed: bool) -> bool:
        """Updates a topic's remaining study hours and completion status."""
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE topics SET remaining_hours = ?, completed = ? WHERE id = ?",
                (remaining_hours, 1 if completed else 0, topic_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_topic(self, topic_id: int) -> bool:
        """Deletes a topic by ID."""
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM topics WHERE id = ?", (topic_id,))
            conn.commit()
            return cursor.rowcount > 0

    # -------------------------------------------------------------------------
    # EXAM CRUD
    # -------------------------------------------------------------------------

    def add_exam(self, subject_id: int, exam_date: str) -> int:
        """Adds an exam date for a subject."""
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO exams (subject_id, exam_date) VALUES (?, ?)", (subject_id, exam_date))
            # Also sync topics under this subject with the exam_date if not set
            cursor.execute("UPDATE topics SET exam_date = ? WHERE subject_id = ?", (exam_date, subject_id))
            conn.commit()
            return cursor.lastrowid

    def get_exams(self, subject_id: Optional[int] = None) -> List[Exam]:
        """Retrieves all exams."""
        with self.get_conn() as conn:
            cursor = conn.cursor()
            if subject_id is not None:
                cursor.execute(
                    """
                    SELECT e.id, e.subject_id, s.name as subject_name, e.exam_date
                    FROM exams e
                    JOIN subjects s ON e.subject_id = s.id
                    WHERE e.subject_id = ?
                    ORDER BY e.exam_date ASC
                    """,
                    (subject_id,)
                )
            else:
                cursor.execute(
                    """
                    SELECT e.id, e.subject_id, s.name as subject_name, e.exam_date
                    FROM exams e
                    JOIN subjects s ON e.subject_id = s.id
                    ORDER BY e.exam_date ASC
                    """
                )
            rows = cursor.fetchall()
            return [Exam(id=r["id"], subject_id=r["subject_id"], subject_name=r["subject_name"], exam_date=r["exam_date"]) for r in rows]

    # -------------------------------------------------------------------------
    # DEPENDENCY / PREREQUISITE CRUD
    # -------------------------------------------------------------------------

    def add_prerequisite(self, topic_id: int, prerequisite_topic_id: int) -> bool:
        """Adds a prerequisite dependency: prerequisite_topic_id must be completed before topic_id."""
        if topic_id == prerequisite_topic_id:
            raise ValueError("A topic cannot be a prerequisite of itself.")

        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO dependencies (topic_id, prerequisite_topic_id) VALUES (?, ?)",
                (topic_id, prerequisite_topic_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def remove_prerequisite(self, topic_id: int, prerequisite_topic_id: int) -> bool:
        """Removes a prerequisite dependency."""
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM dependencies WHERE topic_id = ? AND prerequisite_topic_id = ?",
                (topic_id, prerequisite_topic_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_prerequisites(self, topic_id: int) -> List[int]:
        """Returns list of prerequisite topic IDs for a given topic."""
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT prerequisite_topic_id FROM dependencies WHERE topic_id = ?", (topic_id,))
            return [r["prerequisite_topic_id"] for r in cursor.fetchall()]

    # -------------------------------------------------------------------------
    # STUDY SESSION CRUD
    # -------------------------------------------------------------------------

    def save_study_session(self, session: StudySession) -> int:
        """Saves a generated study session to the database."""
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO study_sessions (topic_id, date, start_time, end_time, duration_hours, priority_score, completed)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.topic_id,
                    session.date,
                    session.start_time,
                    session.end_time,
                    session.duration_hours,
                    session.priority_score,
                    1 if session.completed else 0
                )
            )
            conn.commit()
            return cursor.lastrowid

    def save_study_sessions(self, sessions: List[StudySession]) -> List[int]:
        """Bulk saves multiple study sessions."""
        session_ids: List[int] = []
        for s in sessions:
            sid = self.save_study_session(s)
            session_ids.append(sid)
        return session_ids

    def get_study_sessions(self, date_str: Optional[str] = None) -> List[StudySession]:
        """Retrieves study sessions, optionally filtered by date YYYY-MM-DD."""
        with self.get_conn() as conn:
            cursor = conn.cursor()
            if date_str:
                cursor.execute(
                    """
                    SELECT ss.id, ss.topic_id, t.name as topic_name, s.name as subject_name,
                           ss.date, ss.start_time, ss.end_time, ss.duration_hours, ss.priority_score, ss.completed
                    FROM study_sessions ss
                    JOIN topics t ON ss.topic_id = t.id
                    JOIN subjects s ON t.subject_id = s.id
                    WHERE ss.date = ?
                    ORDER BY ss.start_time ASC
                    """,
                    (date_str,)
                )
            else:
                cursor.execute(
                    """
                    SELECT ss.id, ss.topic_id, t.name as topic_name, s.name as subject_name,
                           ss.date, ss.start_time, ss.end_time, ss.duration_hours, ss.priority_score, ss.completed
                    FROM study_sessions ss
                    JOIN topics t ON ss.topic_id = t.id
                    JOIN subjects s ON t.subject_id = s.id
                    ORDER BY ss.date DESC, ss.start_time ASC
                    """
                )
            rows = cursor.fetchall()
            return [
                StudySession(
                    id=r["id"],
                    topic_id=r["topic_id"],
                    topic_name=r["topic_name"],
                    subject_name=r["subject_name"],
                    date=r["date"],
                    start_time=r["start_time"],
                    end_time=r["end_time"],
                    duration_hours=r["duration_hours"],
                    priority_score=r["priority_score"],
                    completed=bool(r["completed"])
                )
                for r in rows
            ]

    def update_session_completion(self, session_id: int, completed: bool) -> bool:
        """Marks a study session as completed or pending."""
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE study_sessions SET completed = ? WHERE id = ?",
                (1 if completed else 0, session_id)
            )
            conn.commit()
            return cursor.rowcount > 0
