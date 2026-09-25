"""
tests/test_database.py
Unit tests for SQLite Database persistence, foreign key enforcement, and CRUD layer.
"""

import os
import tempfile
import sqlite3
import gc
import pytest

from database.db import DatabaseManager, init_db
from dsa.models import Subject, Topic, StudySession
from dsa.scheduler import GreedyScheduler


@pytest.fixture
def temp_db():
    """Fixture providing a temporary SQLite database file path initialized with schema."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(db_path)
    db = DatabaseManager(db_path)
    yield db
    gc.collect()
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except OSError:
        pass


def test_db_initialization_and_tables(temp_db):
    """Verifies that all tables are properly initialized in SQLite."""
    with temp_db.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row["name"] for row in cursor.fetchall()}
        expected = {"subjects", "topics", "exams", "dependencies", "study_sessions"}
        assert expected.issubset(tables)


def test_subject_crud_operations(temp_db):
    """Tests subject insertion, retrieval, and deletion."""
    s1_id = temp_db.add_subject("DSA")
    s2_id = temp_db.add_subject("DBMS")

    subjects = temp_db.get_subjects()
    assert len(subjects) == 2
    assert subjects[0].name == "DBMS"
    assert subjects[1].name == "DSA"

    subject = temp_db.get_subject_by_id(s1_id)
    assert subject is not None
    assert subject.name == "DSA"

    assert temp_db.delete_subject(s1_id) is True
    assert temp_db.get_subject_by_id(s1_id) is None


def test_topic_and_dependency_crud(temp_db):
    """Tests topic insertion, prerequisite links, and querying."""
    s_id = temp_db.add_subject("DSA")

    t1_id = temp_db.add_topic(
        subject_id=s_id,
        name="Arrays",
        difficulty=3,
        estimated_hours=2.0,
        importance=4,
        exam_date="2026-10-01"
    )

    t2_id = temp_db.add_topic(
        subject_id=s_id,
        name="Trees",
        difficulty=4,
        estimated_hours=3.0,
        importance=5,
        exam_date="2026-10-01",
        prerequisites=[t1_id]
    )

    topics = temp_db.get_topics()
    assert len(topics) == 2

    arrays_topic = [t for t in topics if t.id == t1_id][0]
    trees_topic = [t for t in topics if t.id == t2_id][0]

    assert arrays_topic.name == "Arrays"
    assert arrays_topic.subject_name == "DSA"
    assert arrays_topic.prerequisites == []

    assert trees_topic.name == "Trees"
    assert trees_topic.prerequisites == [t1_id]


def test_foreign_key_enforcement(temp_db):
    """Verifies that SQLite foreign keys prevent orphaned topic or dependency records."""
    # Attempt to insert a topic referencing a non-existent subject_id=9999
    with pytest.raises(sqlite3.IntegrityError):
        temp_db.add_topic(subject_id=9999, name="Orphan Topic")

    # Insert a valid subject and topic
    s_id = temp_db.add_subject("Operating Systems")
    t_id = temp_db.add_topic(subject_id=s_id, name="Processes")

    # Attempt to insert a prerequisite dependency referencing non-existent prerequisite_topic_id=8888
    with pytest.raises(sqlite3.IntegrityError):
        temp_db.add_prerequisite(topic_id=t_id, prerequisite_topic_id=8888)


def test_data_persistence_across_connection_close(temp_db):
    """Verifies that data persists when the database connection is closed and reopened."""
    db_path = temp_db.db_path

    # Step 1: Write data using first connection pool
    s_id = temp_db.add_subject("Computer Networks")
    t_id = temp_db.add_topic(
        subject_id=s_id,
        name="TCP/IP",
        difficulty=4,
        estimated_hours=5.0,
        importance=4
    )

    session = StudySession(
        topic_id=t_id,
        topic_name="TCP/IP",
        subject_name="Computer Networks",
        date="2026-09-25",
        start_time="09:00",
        end_time="10:30",
        duration_hours=1.5,
        priority_score=150.0
    )
    sess_id = temp_db.save_study_session(session)

    # Step 2: Simulate complete application shutdown and restart by creating a new DatabaseManager instance
    reopened_db = DatabaseManager(db_path)

    reopened_subjects = reopened_db.get_subjects()
    assert len(reopened_subjects) == 1
    assert reopened_subjects[0].name == "Computer Networks"

    reopened_topics = reopened_db.get_topics()
    assert len(reopened_topics) == 1
    assert reopened_topics[0].name == "TCP/IP"
    assert reopened_topics[0].estimated_hours == 5.0

    reopened_sessions = reopened_db.get_study_sessions(date_str="2026-09-25")
    assert len(reopened_sessions) == 1
    assert reopened_sessions[0].topic_name == "TCP/IP"
    assert reopened_sessions[0].duration_hours == 1.5


def test_study_sessions_saving_and_retrieval(temp_db):
    """Tests saving generated study sessions and marking completion."""
    s_id = temp_db.add_subject("Math")
    t_id = temp_db.add_topic(subject_id=s_id, name="Linear Algebra", estimated_hours=4.0)

    session = StudySession(
        topic_id=t_id,
        topic_name="Linear Algebra",
        subject_name="Math",
        date="2026-09-25",
        start_time="14:00",
        end_time="15:30",
        duration_hours=1.5,
        priority_score=110.0,
        completed=False
    )

    sid = temp_db.save_study_session(session)
    assert sid > 0

    sessions = temp_db.get_study_sessions(date_str="2026-09-25")
    assert len(sessions) == 1
    assert sessions[0].completed is False

    # Mark session as completed
    assert temp_db.update_session_completion(sid, completed=True) is True
    updated_sessions = temp_db.get_study_sessions(date_str="2026-09-25")
    assert updated_sessions[0].completed is True


def test_scheduler_integration_with_db_data(temp_db):
    """
    End-to-end integration test: Loads topics from DB, feeds them into GreedyScheduler,
    and persists generated study sessions back into DB.
    """
    s_id = temp_db.add_subject("DSA")
    t1_id = temp_db.add_topic(subject_id=s_id, name="Arrays", difficulty=3, estimated_hours=2.0, importance=4, exam_date="2026-10-01")
    t2_id = temp_db.add_topic(subject_id=s_id, name="Graphs", difficulty=5, estimated_hours=4.0, importance=5, exam_date="2026-09-26", prerequisites=[t1_id])

    # 1. Retrieve topics from database
    db_topics = temp_db.get_topics()
    assert len(db_topics) == 2

    # 2. Run GreedyScheduler
    scheduler = GreedyScheduler(max_session_duration=1.5)
    result = scheduler.generate_daily_schedule(db_topics, daily_available_hours=3.0)

    # 3. Save generated sessions back to DB
    generated_sessions = result["sessions"]
    saved_ids = temp_db.save_study_sessions(generated_sessions)

    assert len(saved_ids) == len(generated_sessions)
    assert len(saved_ids) > 0

    # 4. Verify persisted sessions in database
    db_sessions = temp_db.get_study_sessions()
    assert len(db_sessions) == len(generated_sessions)
