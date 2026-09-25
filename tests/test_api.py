"""
tests/test_api.py
Unit tests for Flask REST API endpoints using Flask test_client.
"""

import os
import tempfile
import pytest
from app import create_app
from database.db import init_db


@pytest.fixture
def api_client():
    """Fixture initializing a clean Flask test client with an isolated temporary database."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(db_path)

    app = create_app(db_path)
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client

    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except OSError:
        pass


def test_create_and_get_subject(api_client):
    """Tests POST /api/subjects (201) and GET /api/subjects (200)."""
    response = api_client.post("/api/subjects", json={"name": "DSA"})
    assert response.status_code == 201
    data = response.get_json()
    assert data["id"] > 0
    assert data["name"] == "DSA"

    get_resp = api_client.get("/api/subjects")
    assert get_resp.status_code == 200
    subjects = get_resp.get_json()
    assert len(subjects) == 1
    assert subjects[0]["name"] == "DSA"


def test_create_and_get_topic(api_client):
    """Tests POST /api/topics (201), GET /api/topics (200), and GET /api/topics/<id> (200)."""
    subj_resp = api_client.post("/api/subjects", json={"name": "DBMS"})
    subj_id = subj_resp.get_json()["id"]

    topic_payload = {
        "subject_id": subj_id,
        "name": "Normalization",
        "difficulty": 4,
        "estimated_hours": 3.0,
        "importance": 5,
        "exam_date": "2026-10-15"
    }

    create_resp = api_client.post("/api/topics", json=topic_payload)
    assert create_resp.status_code == 201
    topic_data = create_resp.get_json()
    topic_id = topic_data["id"]

    assert topic_data["name"] == "Normalization"
    assert topic_data["subject_name"] == "DBMS"
    assert topic_data["difficulty"] == 4

    get_resp = api_client.get(f"/api/topics/{topic_id}")
    assert get_resp.status_code == 200
    assert get_resp.get_json()["name"] == "Normalization"


def test_create_prerequisite(api_client):
    """Tests creating prerequisite linkage via POST /api/topics/<id>/prerequisites."""
    subj_resp = api_client.post("/api/subjects", json={"name": "DSA"})
    subj_id = subj_resp.get_json()["id"]

    t1_resp = api_client.post("/api/topics", json={"subject_id": subj_id, "name": "Arrays"})
    t2_resp = api_client.post("/api/topics", json={"subject_id": subj_id, "name": "Trees"})

    t1_id = t1_resp.get_json()["id"]
    t2_id = t2_resp.get_json()["id"]

    prereq_resp = api_client.post(f"/api/topics/{t2_id}/prerequisites", json={"prerequisite_topic_id": t1_id})
    assert prereq_resp.status_code == 200
    updated_topic = prereq_resp.get_json()
    assert t1_id in updated_topic["prerequisites"]


def test_generate_schedule_api(api_client):
    """Tests POST /api/schedule/generate triggering Greedy Max-Heap Scheduler."""
    subj_resp = api_client.post("/api/subjects", json={"name": "DSA"})
    subj_id = subj_resp.get_json()["id"]

    api_client.post("/api/topics", json={"subject_id": subj_id, "name": "Graphs", "difficulty": 5, "estimated_hours": 4.0, "exam_date": "2026-09-28"})

    sched_resp = api_client.post("/api/schedule/generate", json={
        "daily_available_hours": 3.0,
        "target_date": "2026-09-26",
        "max_session_duration": 1.5
    })

    assert sched_resp.status_code == 200
    sched_data = sched_resp.get_json()

    assert "sessions" in sched_data
    assert "total_hours_scheduled" in sched_data
    assert "topological_order" in sched_data
    assert "has_cycle" in sched_data

    assert sched_data["total_hours_scheduled"] == 3.0
    assert len(sched_data["sessions"]) == 2  # 1.5h + 1.5h sessions


def test_retrieve_generated_sessions(api_client):
    """Tests GET /api/sessions retrieving persisted study sessions."""
    subj_resp = api_client.post("/api/subjects", json={"name": "Math"})
    subj_id = subj_resp.get_json()["id"]
    api_client.post("/api/topics", json={"subject_id": subj_id, "name": "Calculus", "estimated_hours": 2.0})

    api_client.post("/api/schedule/generate", json={"daily_available_hours": 2.0, "target_date": "2026-09-26"})

    sessions_resp = api_client.get("/api/sessions?date=2026-09-26")
    assert sessions_resp.status_code == 200
    sessions = sessions_resp.get_json()
    assert len(sessions) > 0
    assert sessions[0]["topic_name"] == "Calculus"


def test_update_topic_progress_and_session_completion(api_client):
    """Tests PATCH /api/topics/<id>/progress and PATCH /api/sessions/<id>/complete."""
    subj_resp = api_client.post("/api/subjects", json={"name": "DSA"})
    subj_id = subj_resp.get_json()["id"]
    t_resp = api_client.post("/api/topics", json={"subject_id": subj_id, "name": "Stacks", "estimated_hours": 3.0})
    t_id = t_resp.get_json()["id"]

    # Update progress
    progress_resp = api_client.patch(f"/api/topics/{t_id}/progress", json={"remaining_hours": 1.0})
    assert progress_resp.status_code == 200
    assert progress_resp.get_json()["remaining_hours"] == 1.0

    # Generate session and update completion
    sched_resp = api_client.post("/api/schedule/generate", json={"daily_available_hours": 1.0})
    sess_id = sched_resp.get_json()["sessions"][0]["id"]

    sess_comp_resp = api_client.patch(f"/api/sessions/{sess_id}/complete", json={"completed": True})
    assert sess_comp_resp.status_code == 200


def test_invalid_input_validations(api_client):
    """Tests validation errors returning 400 Bad Request."""
    # Blank subject name
    assert api_client.post("/api/subjects", json={"name": ""}).status_code == 400

    # Subject ID does not exist for topic creation
    assert api_client.post("/api/topics", json={"subject_id": 999, "name": "Invalid Subj"}).status_code == 400

    # Difficulty out of bounds (6)
    subj_id = api_client.post("/api/subjects", json={"name": "Test Subj"}).get_json()["id"]
    assert api_client.post("/api/topics", json={"subject_id": subj_id, "name": "Test", "difficulty": 6}).status_code == 400

    # Negative hours
    assert api_client.post("/api/topics", json={"subject_id": subj_id, "name": "Test", "estimated_hours": -2.0}).status_code == 400

    # Missing daily_available_hours in schedule generation
    assert api_client.post("/api/schedule/generate", json={}).status_code == 400


def test_nonexistent_resource(api_client):
    """Tests 404 Not Found error responses."""
    assert api_client.get("/api/topics/9999").status_code == 404
    assert api_client.delete("/api/subjects/9999").status_code == 404


def test_end_to_end_api_db_dsa_integration(api_client):
    """
    Full end-to-end integration test:
    API -> PlannerService -> DatabaseManager (SQLite) -> GreedyScheduler & PriorityQueue (DSA).
    """
    # 1. Create Subject
    s_resp = api_client.post("/api/subjects", json={"name": "Software Engineering"})
    s_id = s_resp.get_json()["id"]

    # 2. Add Prerequisites Chain: Arrays -> Searching -> Dynamic Programming
    t1 = api_client.post("/api/topics", json={"subject_id": s_id, "name": "Arrays", "difficulty": 2, "estimated_hours": 1.0, "exam_date": "2026-09-30"}).get_json()["id"]
    t2 = api_client.post("/api/topics", json={"subject_id": s_id, "name": "Searching", "difficulty": 3, "estimated_hours": 2.0, "exam_date": "2026-09-30", "prerequisites": [t1]}).get_json()["id"]
    t3 = api_client.post("/api/topics", json={"subject_id": s_id, "name": "Dynamic Programming", "difficulty": 5, "estimated_hours": 4.0, "exam_date": "2026-09-28", "prerequisites": [t2]}).get_json()["id"]

    # 3. Request Schedule Generation via API (daily_available_hours = 3.0)
    gen_resp = api_client.post("/api/schedule/generate", json={"daily_available_hours": 3.0, "target_date": "2026-09-26"})
    assert gen_resp.status_code == 200
    plan = gen_resp.get_json()

    # Slot 1: Arrays (1.0h -> finishes, unlocks Searching!)
    # Slot 2 & 3: Searching (1.5h + 0.5h -> finishes, unlocks Dynamic Programming!)
    sessions = plan["sessions"]
    assert len(sessions) >= 2
    assert sessions[0]["topic_name"] == "Arrays"
    assert sessions[1]["topic_name"] == "Searching"

    # 4. Verify persisted sessions via GET /api/sessions
    all_sess = api_client.get("/api/sessions").get_json()
    assert len(all_sess) == len(sessions)
