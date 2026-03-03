"""
SQLite-based observability logger for the Market Trend Analyzer.
Stores runs, state transitions, and tool call logs for full auditability.
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import List, Optional


DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(DB_DIR, "runs.db")


class DBLogger:
    """Persistent SQLite logger for agent runs."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    # ── Schema Setup ──────────────────────────────────────────────

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS runs (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id      TEXT UNIQUE NOT NULL,
                    seed        INTEGER,
                    started_at  TEXT,
                    finished_at TEXT,
                    status      TEXT DEFAULT 'RUNNING'
                );

                CREATE TABLE IF NOT EXISTS transitions (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id      TEXT NOT NULL,
                    prev_state  TEXT NOT NULL,
                    event       TEXT NOT NULL,
                    next_state  TEXT NOT NULL,
                    timestamp   TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                );

                CREATE TABLE IF NOT EXISTS tool_calls (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id          TEXT NOT NULL,
                    tool_name       TEXT NOT NULL,
                    input_json      TEXT,
                    output_json     TEXT,
                    duration_secs   REAL,
                    success         INTEGER DEFAULT 1,
                    error_message   TEXT,
                    timestamp       TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                );
            """)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ── Run Lifecycle ─────────────────────────────────────────────

    def start_run(self, run_id: str, seed: int):
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO runs (run_id, seed, started_at, status) VALUES (?, ?, ?, ?)",
                (run_id, seed, datetime.now().isoformat(), "RUNNING"),
            )

    def finish_run(self, run_id: str, status: str = "COMPLETED"):
        with self._connect() as conn:
            conn.execute(
                "UPDATE runs SET finished_at = ?, status = ? WHERE run_id = ?",
                (datetime.now().isoformat(), status, run_id),
            )

    # ── Transition Logging ────────────────────────────────────────

    def log_transition(self, run_id: str, prev_state: str, event: str, next_state: str):
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO transitions (run_id, prev_state, event, next_state, timestamp) "
                "VALUES (?, ?, ?, ?, ?)",
                (run_id, prev_state, event, next_state, datetime.now().isoformat()),
            )

    # ── Tool Call Logging ─────────────────────────────────────────

    def log_tool_call(
        self,
        run_id: str,
        tool_name: str,
        input_data: dict,
        output_data: dict,
        duration: float,
        success: bool = True,
        error_message: Optional[str] = None,
    ):
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO tool_calls "
                "(run_id, tool_name, input_json, output_json, duration_secs, success, error_message, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    tool_name,
                    json.dumps(input_data, default=str),
                    json.dumps(output_data, default=str),
                    duration,
                    int(success),
                    error_message,
                    datetime.now().isoformat(),
                ),
            )

    # ── Queries ───────────────────────────────────────────────────

    def get_run(self, run_id: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            return dict(row) if row else None

    def get_transitions(self, run_id: str) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM transitions WHERE run_id = ? ORDER BY id", (run_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_tool_calls(self, run_id: str) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM tool_calls WHERE run_id = ? ORDER BY id", (run_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_recent_runs(self, limit: int = 10) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    # ── Auto Seed Management ──────────────────────────────────────

    def get_next_seed(self) -> int:
        """Get the next seed by incrementing the max seed in the database.
        If no runs exist, starts from 1."""
        with self._connect() as conn:
            row = conn.execute("SELECT MAX(seed) as max_seed FROM runs").fetchone()
            max_seed = row["max_seed"] if row and row["max_seed"] is not None else 0
            return max_seed + 1

    def get_seed_history(self, limit: int = 50) -> List[dict]:
        """Fetch seed history for UI display."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT run_id, seed, started_at as timestamp FROM runs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
