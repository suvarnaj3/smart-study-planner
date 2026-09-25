"""
app.py
Flask REST API and Frontend Web Server for Smart Study Planner.

Provides clean HTTP endpoints for Subjects, Topics, Exams, Prerequisites,
Greedy Max-Heap Schedule Generation, and Progress Tracking.

Architecture Flow:
HTTP Client / Browser -> Flask Route (app.py) -> PlannerService (services/) -> DatabaseManager (database/) + DSA (dsa/)
"""

import os
from typing import Dict, Any, Tuple
from flask import Flask, request, jsonify, render_template, Response
from database.db import DatabaseManager, init_db
from services.planner_service import PlannerService


def create_app(db_path: str = "planner.db") -> Flask:
    """
    Application factory for Flask REST API.
    """
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["DB_PATH"] = db_path

    # Initialize DB schema if running on file-based DB
    if db_path != ":memory:" and not os.path.exists(db_path):
        init_db(db_path)

    db_manager = DatabaseManager(db_path)
    service = PlannerService(db_manager)

    # Lightweight CORS headers handler
    @app.after_request
    def add_cors_headers(response: Response) -> Response:
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        return response

    @app.route("/api/options-handler", methods=["OPTIONS"])
    def handle_options():
        return "", 200

    # -------------------------------------------------------------------------
    # FRONTEND PAGE ROUTE
    # -------------------------------------------------------------------------

    @app.route("/", methods=["GET"])
    def index_page():
        return render_template("index.html")

    # Global Error Handlers
    @app.errorhandler(404)
    def not_found_error(error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Resource not found"}), 404
        return render_template("index.html"), 200

    @app.errorhandler(500)
    def internal_error(error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Internal server error"}), 500
        return "Internal server error", 500

    # -------------------------------------------------------------------------
    # HEALTH CHECK
    # -------------------------------------------------------------------------

    @app.route("/api/health", methods=["GET"])
    def health_check():
        return jsonify({"status": "ok", "app": "Smart Study Planner"}), 200

    # -------------------------------------------------------------------------
    # SUBJECT ROUTES
    # -------------------------------------------------------------------------

    @app.route("/api/subjects", methods=["GET"])
    def get_subjects():
        subjects = service.get_all_subjects()
        return jsonify(subjects), 200

    @app.route("/api/subjects", methods=["POST"])
    def create_subject():
        data = request.get_json() or {}
        name = data.get("name")
        if not name:
            return jsonify({"error": "Missing required field 'name'"}), 400

        try:
            subject = service.create_subject(name)
            return jsonify(subject), 201
        except ValueError as ve:
            return jsonify({"error": str(ve)}), 400

    @app.route("/api/subjects/<int:subject_id>", methods=["DELETE"])
    def delete_subject(subject_id: int):
        success = service.delete_subject(subject_id)
        if not success:
            return jsonify({"error": f"Subject ID {subject_id} not found"}), 404
        return jsonify({"message": "Subject deleted successfully"}), 200

    # -------------------------------------------------------------------------
    # TOPIC ROUTES
    # -------------------------------------------------------------------------

    @app.route("/api/topics", methods=["GET"])
    def get_topics():
        subject_id_param = request.args.get("subject_id")
        subject_id = int(subject_id_param) if subject_id_param and subject_id_param.isdigit() else None
        topics = service.get_all_topics(subject_id=subject_id)
        return jsonify(topics), 200

    @app.route("/api/topics/<int:topic_id>", methods=["GET"])
    def get_topic(topic_id: int):
        topic = service.get_topic_by_id(topic_id)
        if not topic:
            return jsonify({"error": f"Topic ID {topic_id} not found"}), 404
        return jsonify(topic), 200

    @app.route("/api/topics", methods=["POST"])
    def create_topic():
        data = request.get_json() or {}
        subject_id = data.get("subject_id")
        name = data.get("name")

        if subject_id is None or not name:
            return jsonify({"error": "Missing required fields 'subject_id' or 'name'"}), 400

        difficulty = data.get("difficulty", 3)
        estimated_hours = data.get("estimated_hours", 1.0)
        importance = data.get("importance", 3)
        exam_date = data.get("exam_date")
        remaining_hours = data.get("remaining_hours")
        prerequisites = data.get("prerequisites")

        try:
            topic = service.create_topic(
                subject_id=int(subject_id),
                name=str(name),
                difficulty=int(difficulty),
                estimated_hours=float(estimated_hours),
                importance=int(importance),
                exam_date=exam_date,
                remaining_hours=float(remaining_hours) if remaining_hours is not None else None,
                prerequisites=prerequisites
            )
            return jsonify(topic), 201
        except ValueError as ve:
            return jsonify({"error": str(ve)}), 400

    @app.route("/api/topics/<int:topic_id>", methods=["DELETE"])
    def delete_topic(topic_id: int):
        success = service.delete_topic(topic_id)
        if not success:
            return jsonify({"error": f"Topic ID {topic_id} not found"}), 404
        return jsonify({"message": "Topic deleted successfully"}), 200

    @app.route("/api/topics/<int:topic_id>/progress", methods=["PATCH", "PUT"])
    def update_topic_progress(topic_id: int):
        data = request.get_json() or {}
        remaining_hours = data.get("remaining_hours")
        completed = data.get("completed")

        try:
            updated_topic = service.update_topic_progress(
                topic_id=topic_id,
                remaining_hours=float(remaining_hours) if remaining_hours is not None else None,
                completed=bool(completed) if completed is not None else None
            )
            return jsonify(updated_topic), 200
        except ValueError as ve:
            err_msg = str(ve)
            status_code = 404 if "does not exist" in err_msg else 400
            return jsonify({"error": err_msg}), status_code

    # -------------------------------------------------------------------------
    # PREREQUISITE ROUTES
    # -------------------------------------------------------------------------

    @app.route("/api/topics/<int:topic_id>/prerequisites", methods=["POST"])
    def add_prerequisite(topic_id: int):
        data = request.get_json() or {}
        prerequisite_topic_id = data.get("prerequisite_topic_id")
        if prerequisite_topic_id is None:
            return jsonify({"error": "Missing required field 'prerequisite_topic_id'"}), 400

        try:
            topic = service.add_prerequisite(topic_id, int(prerequisite_topic_id))
            return jsonify(topic), 200
        except ValueError as ve:
            err_msg = str(ve)
            status_code = 404 if "does not exist" in err_msg else 400
            return jsonify({"error": err_msg}), status_code

    @app.route("/api/topics/<int:topic_id>/prerequisites/<int:prereq_id>", methods=["DELETE"])
    def remove_prerequisite(topic_id: int, prereq_id: int):
        success = service.remove_prerequisite(topic_id, prereq_id)
        return jsonify({"message": "Prerequisite removed successfully"}), 200

    # -------------------------------------------------------------------------
    # EXAM ROUTES
    # -------------------------------------------------------------------------

    @app.route("/api/exams", methods=["GET"])
    def get_exams():
        subject_id_param = request.args.get("subject_id")
        subject_id = int(subject_id_param) if subject_id_param and subject_id_param.isdigit() else None
        exams = service.get_all_exams(subject_id=subject_id)
        return jsonify(exams), 200

    @app.route("/api/exams", methods=["POST"])
    def create_exam():
        data = request.get_json() or {}
        subject_id = data.get("subject_id")
        exam_date = data.get("exam_date")

        if subject_id is None or not exam_date:
            return jsonify({"error": "Missing required fields 'subject_id' or 'exam_date'"}), 400

        try:
            exam = service.create_exam(int(subject_id), str(exam_date))
            return jsonify(exam), 201
        except ValueError as ve:
            err_msg = str(ve)
            status_code = 404 if "does not exist" in err_msg else 400
            return jsonify({"error": err_msg}), status_code

    # -------------------------------------------------------------------------
    # SCHEDULE GENERATION & SESSION ROUTES
    # -------------------------------------------------------------------------

    @app.route("/api/schedule/generate", methods=["POST"])
    def generate_schedule():
        data = request.get_json() or {}
        daily_available_hours = data.get("daily_available_hours")

        if daily_available_hours is None:
            return jsonify({"error": "Missing required field 'daily_available_hours'"}), 400

        target_date = data.get("target_date")
        max_session_duration = data.get("max_session_duration", 1.5)
        start_time = data.get("start_time", "09:00")

        try:
            result = service.generate_schedule(
                daily_available_hours=float(daily_available_hours),
                target_date_str=target_date,
                max_session_duration=float(max_session_duration),
                start_time_str=str(start_time)
            )
            return jsonify(result), 200
        except ValueError as ve:
            return jsonify({"error": str(ve)}), 400

    @app.route("/api/sessions", methods=["GET"])
    def get_sessions():
        date_param = request.args.get("date")
        try:
            sessions = service.get_study_sessions(date_str=date_param)
            return jsonify(sessions), 200
        except ValueError as ve:
            return jsonify({"error": str(ve)}), 400

    @app.route("/api/sessions/<int:session_id>/complete", methods=["PATCH", "PUT"])
    def update_session_completion(session_id: int):
        data = request.get_json() or {}
        completed = data.get("completed", True)

        success = service.update_session_completion(session_id, bool(completed))
        if not success:
            return jsonify({"error": f"Session ID {session_id} not found"}), 404

        return jsonify({"message": "Session completion updated successfully"}), 200

    return app


app = create_app("planner.db")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
