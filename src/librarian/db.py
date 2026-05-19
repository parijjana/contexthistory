import os
import sqlite3
import logging
import traceback
from datetime import datetime

# Standardize DB Names
ARCHEOLOGY_DB = "memory_archeology.db"
ORCHESTRATION_DB = "memory_orchestration.db"
PURGATORY_DB = "memory_purgatory.db"

logger = logging.getLogger("Librarian.DB")

def connect_db(db_path: str, timeout: float = 10.0) -> sqlite3.Connection:
    """Connects to SQLite with WAL mode enabled for high concurrency."""
    conn = sqlite3.connect(db_path, timeout=timeout)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the Dual-Brain, Purgatory, and Telemetry schemas with defensive migrations."""
    try:
        # 1. Archeology DB (The High-Fidelity Brain)
        with connect_db(ARCHEOLOGY_DB) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trace_matrix (
                    feat_id TEXT, file_path TEXT, test_id TEXT, description TEXT, 
                    last_updated DATETIME, line_count INTEGER, size_bytes INTEGER, 
                    git_sha TEXT, status TEXT DEFAULT 'ACTIVE', last_commit_msg TEXT,
                    PRIMARY KEY (feat_id, file_path)
                )
            """)
            # Migration: Ensure status and last_commit_msg exist if table was created by older version
            existing_cols = [row[1] for row in conn.execute("PRAGMA table_info(trace_matrix)").fetchall()]
            if "status" not in existing_cols:
                conn.execute("ALTER TABLE trace_matrix ADD COLUMN status TEXT DEFAULT 'ACTIVE'")
            if "last_commit_msg" not in existing_cols:
                conn.execute("ALTER TABLE trace_matrix ADD COLUMN last_commit_msg TEXT")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS decision_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, feat_id TEXT, file_path TEXT, 
                    timestamp DATETIME, decision TEXT, rationale TEXT, trade_offs TEXT,
                    tag_hash TEXT UNIQUE, git_sha TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_archive (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, feat_id TEXT, 
                    file_path TEXT, content_json TEXT, archived_at DATETIME, 
                    reason TEXT, magnitude INTEGER DEFAULT 0, git_sha TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_stats (
                    file_path TEXT PRIMARY KEY, change_count INTEGER DEFAULT 0,
                    last_size_bytes INTEGER, total_magnitude_bytes INTEGER DEFAULT 0,
                    last_updated DATETIME, last_sha TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS parked_tests (
                    test_id TEXT PRIMARY KEY, file_path TEXT, last_seen DATETIME
                )
            """)
            # Sync History for Timeline
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME, 
                    mode TEXT, files_processed INTEGER, items_updated INTEGER
                )
            """)
            conn.commit()

        # 2. Purgatory DB (Safety Net)
        with connect_db(PURGATORY_DB) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS trace_matrix (feat_id TEXT, file_path TEXT, test_id TEXT, description TEXT, last_updated DATETIME, line_count INTEGER, size_bytes INTEGER, git_sha TEXT, status TEXT, last_commit_msg TEXT, PRIMARY KEY (feat_id, file_path))")
            # Migration for Purgatory
            existing_cols = [row[1] for row in conn.execute("PRAGMA table_info(trace_matrix)").fetchall()]
            if "status" not in existing_cols:
                conn.execute("ALTER TABLE trace_matrix ADD COLUMN status TEXT")
            if "last_commit_msg" not in existing_cols:
                conn.execute("ALTER TABLE trace_matrix ADD COLUMN last_commit_msg TEXT")
                
            conn.execute("CREATE TABLE IF NOT EXISTS decision_log (id INTEGER PRIMARY KEY AUTOINCREMENT, feat_id TEXT, file_path TEXT, timestamp DATETIME, decision TEXT, rationale TEXT, trade_offs TEXT, tag_hash TEXT UNIQUE, git_sha TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS memory_archive (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, feat_id TEXT, file_path TEXT, content_json TEXT, archived_at DATETIME, reason TEXT, magnitude INTEGER DEFAULT 0, git_sha TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS file_stats (file_path TEXT PRIMARY KEY, change_count INTEGER DEFAULT 0, last_size_bytes INTEGER, total_magnitude_bytes INTEGER DEFAULT 0, last_updated DATETIME, last_sha TEXT)")
            conn.commit()

        # 3. Orchestration DB (Telemetry & Ops)
        with connect_db(ORCHESTRATION_DB) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS amnesia_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME, 
                    file_path TEXT, incident_report TEXT, type TEXT DEFAULT 'DEFINITE'
                )
            """)
            # Tool Usage Telemetry
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tool_usage_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME, 
                    tool_name TEXT, feat_id TEXT, result_status TEXT
                )
            """)
            conn.execute("CREATE TABLE IF NOT EXISTS session_state (feat_id TEXT PRIMARY KEY, s_code INTEGER, tasks_json TEXT, last_updated DATETIME)")
            conn.execute("CREATE TABLE IF NOT EXISTS validation_history (session_id TEXT PRIMARY KEY, feat_id TEXT, status TEXT, t_start DATETIME, t_end DATETIME, summary_path TEXT)")
            conn.commit()
    except Exception:
        logger.error(f"Database init failed: {traceback.format_exc()}")
        raise
