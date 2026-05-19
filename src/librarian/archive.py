import json
import hashlib
from datetime import datetime
from typing import Dict, Optional
import sqlite3

def archive_record(conn: sqlite3.Connection, type: str, feat_id: str, file_path: str, data: dict, reason: str, magnitude: int = 0, sha: str = "PROTO"):
    """Saves a point-in-time logical state to the archive."""
    conn.execute("""
        INSERT INTO memory_archive (type, feat_id, file_path, content_json, archived_at, reason, magnitude, git_sha) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (type, feat_id, file_path, json.dumps(data), datetime.now(), reason, magnitude, sha))

def log_amnesia(conn: sqlite3.Connection, file_path: str, message: str, amnesia_type: str = 'DEFINITE'):
    """Logs an automated or manual amnesia event."""
    conn.execute("""
        INSERT INTO amnesia_log (timestamp, file_path, incident_report, type) 
        VALUES (?, ?, ?, ?)
    """, (datetime.now(), file_path, message, amnesia_type))
    conn.commit()

def get_tag_hash(feat_id: str, decision: str, rationale: str) -> str:
    """Generates a unique hash for a decision tag to prevent duplicates."""
    payload = f"{feat_id}{decision}{rationale}".encode()
    return hashlib.md5(payload).hexdigest()
