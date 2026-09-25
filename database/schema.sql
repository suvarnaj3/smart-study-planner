-- database/schema.sql
-- SQLite Database Schema for Smart Study Planner

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    difficulty INTEGER NOT NULL CHECK (difficulty BETWEEN 1 AND 5),
    estimated_hours REAL NOT NULL CHECK (estimated_hours >= 0),
    remaining_hours REAL NOT NULL CHECK (remaining_hours >= 0),
    importance INTEGER NOT NULL CHECK (importance BETWEEN 1 AND 5),
    exam_date TEXT,
    completed INTEGER NOT NULL DEFAULT 0 CHECK (completed IN (0, 1)),
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL,
    exam_date TEXT NOT NULL,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dependencies (
    topic_id INTEGER NOT NULL,
    prerequisite_topic_id INTEGER NOT NULL,
    PRIMARY KEY (topic_id, prerequisite_topic_id),
    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE,
    FOREIGN KEY (prerequisite_topic_id) REFERENCES topics(id) ON DELETE CASCADE,
    CHECK (topic_id != prerequisite_topic_id)
);

CREATE TABLE IF NOT EXISTS study_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    duration_hours REAL NOT NULL CHECK (duration_hours > 0),
    priority_score REAL NOT NULL DEFAULT 0.0,
    completed INTEGER NOT NULL DEFAULT 0 CHECK (completed IN (0, 1)),
    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
);
