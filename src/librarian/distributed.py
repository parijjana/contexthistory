import os
import json
import logging
from pathlib import Path
from datetime import datetime
from .db import connect_db, ARCHEOLOGY_DB

logger = logging.getLogger("Librarian.Distributed")

MEMORY_FOLDER = ".memory"

def export_memory(workspace_root: str, current_sha: str):
    """
    Exports the current active logical state (traces and decisions) 
    to a JSON file in the .memory/ folder for Git tracking.
    """
    try:
        mem_dir = Path(workspace_root) / MEMORY_FOLDER
        mem_dir.mkdir(exist_ok=True)
        
        # Name file after SHA or timestamp to avoid conflicts in multi-user environments
        filename = f"fossil_{current_sha if current_sha != 'PROTO' else int(datetime.now().timestamp())}.json"
        export_path = mem_dir / filename
        
        data = {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "git_sha": current_sha,
            "traces": [],
            "decisions": []
        }
        
        with connect_db(ARCHEOLOGY_DB) as conn:
            # Only export traces and decisions associated with the current SHA
            # to keep fossil files incremental and relevant to the commit.
            # Explicit column list to avoid SELECT *
            cursor = conn.execute("""
                SELECT feat_id, file_path, test_id, description, last_updated, line_count, size_bytes, git_sha, status, last_commit_msg 
                FROM trace_matrix WHERE git_sha = ?
            """, (current_sha,))
            data["traces"] = [dict(row) for row in cursor.fetchall()]
            
            cursor = conn.execute("""
                SELECT feat_id, file_path, timestamp, decision, rationale, trade_offs, tag_hash, git_sha 
                FROM decision_log WHERE git_sha = ?
            """, (current_sha,))
            data["decisions"] = [dict(row) for row in cursor.fetchall()]

        if data["traces"] or data["decisions"]:
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Exported memory fossil: {filename}")
            
    except Exception as e:
        logger.error(f"Memory Export Failed: {e}")

def import_memory(workspace_root: str):
    """
    Scans the .memory/ folder for fossil files and merges them into the local SQLite brain.
    """
    try:
        mem_dir = Path(workspace_root) / MEMORY_FOLDER
        if not mem_dir.exists(): return
        
        for fossil_file in mem_dir.glob("fossil_*.json"):
            try:
                with open(fossil_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                with connect_db(ARCHEOLOGY_DB) as conn:
                    # 1. Merge Traces
                    for trace in data.get("traces", []):
                        cols = ", ".join(trace.keys())
                        placeholders = ", ".join(["?" for _ in trace])
                        conn.execute(f"INSERT OR IGNORE INTO trace_matrix ({cols}) VALUES ({placeholders})", list(trace.values()))
                    
                    # 2. Merge Decisions
                    for dec in data.get("decisions", []):
                        # Ensure tag_hash uniqueness check is respected
                        cols = ", ".join(dec.keys())
                        placeholders = ", ".join(["?" for _ in dec])
                        conn.execute(f"INSERT OR IGNORE INTO decision_log ({cols}) VALUES ({placeholders})", list(dec.values()))
                    
                    conn.commit()
            except Exception as fe:
                logger.error(f"Failed to ingest fossil {fossil_file}: {fe}")
                
    except Exception as e:
        logger.error(f"Memory Import Failed: {e}")
