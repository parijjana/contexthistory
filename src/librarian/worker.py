import os
import subprocess
import logging
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from .db import connect_db, ARCHEOLOGY_DB, ORCHESTRATION_DB, PURGATORY_DB
from . import parser, discovery, archive, distiller

logger = logging.getLogger("Librarian.Worker")

def get_git_echo(file_path: str, workspace_root: str) -> str:
    """Retrieves the last commit message for a specific file path."""
    try:
        res = subprocess.run(
            ["git", "log", "-1", "--format=%s", "--", file_path],
            capture_output=True, text=True, cwd=workspace_root
        )
        return res.stdout.strip() if res.returncode == 0 else "No git history found."
    except Exception:
        return "Git not available."

def reconcile_purgatory(workspace_root: str, ignore_spec):
    """
    Audits existing memory. 
    1. Files missing from disk but tracked:
       - If ignored by spec -> Move to Purgatory.
       - If NOT ignored (deleted but logic intended) -> Mark as PARKED + Git Echo.
    2. Files in Purgatory/Parked that now exist and are valid -> Restore to ACTIVE.
    """
    try:
        with connect_db(ARCHEOLOGY_DB) as a_conn:
            cursor = a_conn.execute("SELECT DISTINCT file_path, status FROM trace_matrix")
            tracked_data = {row['file_path']: row['status'] for row in cursor.fetchall()}
            
        for fpath, status in tracked_data.items():
            path = Path(fpath)
            rel_path = os.path.relpath(fpath, workspace_root)
            is_ignored = ignore_spec.match_file(rel_path)
            exists = path.exists()

            if is_ignored:
                logger.info(f"Evicting {rel_path} to Purgatory (Ignored).")
                _move_file_data(ARCHEOLOGY_DB, PURGATORY_DB, fpath)
            elif not exists and status != 'PARKED':
                logger.info(f"Parking {rel_path} (Deleted but trace exists).")
                commit_msg = get_git_echo(fpath, workspace_root)
                with connect_db(ARCHEOLOGY_DB) as conn:
                    conn.execute("UPDATE trace_matrix SET status = 'PARKED', last_commit_msg = ? WHERE file_path = ?", (commit_msg, fpath))
                    conn.commit()
            elif exists and status == 'PARKED':
                logger.info(f"Restoring {rel_path} to ACTIVE.")
                with connect_db(ARCHEOLOGY_DB) as conn:
                    conn.execute("UPDATE trace_matrix SET status = 'ACTIVE' WHERE file_path = ?", (fpath,))
                    conn.commit()

        # 3. Restore from Purgatory if no longer ignored
        with connect_db(PURGATORY_DB) as p_conn:
            cursor = p_conn.execute("SELECT DISTINCT file_path FROM trace_matrix")
            purgatory_files = [row['file_path'] for row in cursor.fetchall()]
            
        for fpath in purgatory_files:
            rel_path = os.path.relpath(fpath, workspace_root)
            if not ignore_spec.match_file(rel_path):
                logger.info(f"Restoring {rel_path} from Purgatory (No longer ignored).")
                _move_file_data(PURGATORY_DB, ARCHEOLOGY_DB, fpath)
                
    except Exception as e:
        logger.error(f"Purgatory Reconciliation Failed: {e}")

def _move_file_data(source_db: str, target_db: str, file_path: str):
    tables = ["trace_matrix", "decision_log", "memory_archive", "file_stats"]
    try:
        with connect_db(source_db) as s_conn, connect_db(target_db) as t_conn:
            for table in tables:
                # Explicit column selection based on table schema to avoid SELECT *
                cols_map = {
                    "trace_matrix": "feat_id, file_path, test_id, description, last_updated, line_count, size_bytes, git_sha, status, last_commit_msg",
                    "decision_log": "feat_id, file_path, timestamp, decision, rationale, trade_offs, tag_hash, git_sha",
                    "memory_archive": "type, feat_id, file_path, content_json, archived_at, reason, magnitude, git_sha",
                    "file_stats": "file_path, change_count, last_size_bytes, total_magnitude_bytes, last_updated, last_sha"
                }
                select_cols = cols_map.get(table, "*")
                cursor = s_conn.execute(f"SELECT {select_cols} FROM {table} WHERE file_path = ?", (file_path,))
                rows = [dict(r) for r in cursor.fetchall()]
                for row in rows:
                    cols = ", ".join(row.keys())
                    placeholders = ", ".join(["?" for _ in row])
                    t_conn.execute(f"INSERT OR REPLACE INTO {table} ({cols}) VALUES ({placeholders})", list(row.values()))
                s_conn.execute(f"DELETE FROM {table} WHERE file_path = ?", (file_path,))
            s_conn.commit()
            t_conn.commit()
    except Exception as e:
        logger.error(f"Failed to move data for {file_path}: {e}")

def log_sync_event(mode: str, files: int, updates: int):
    """Records a sync cycle in the history for timeline visualization."""
    try:
        with connect_db(ARCHEOLOGY_DB) as conn:
            conn.execute("INSERT INTO sync_history (timestamp, mode, files_processed, items_updated) VALUES (?, ?, ?, ?)",
                       (datetime.now(), mode, files, updates))
            conn.commit()
    except Exception as e:
        logger.error(f"Sync Telemetry Failed: {e}")

def process_file(file_path: Path, last_sync: float, current_sync: float, magnitude: int, sha: str, config: dict) -> int:
    """Parses a file for traces and decisions, updating the local brain."""
    try:
        if not file_path.exists(): return 0
        
        # Check mtime
        mtime = file_path.stat().st_mtime
        if mtime < last_sync: return 0
        
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
        if not discovery.is_logic_file(content, file_path.suffix, config):
            return 0
            
        tags = parser.parse_tags_multi_line(content)
        updates = 0
        
        # --- AMNESIA DETECTION (Human-Gated Logic) ---
        if not tags["traces"]:
            # 1. Get Onboarding Checkpoint
            onboarded_at = 0.0
            try:
                with connect_db(ORCHESTRATION_DB) as o_conn:
                    row = o_conn.execute("SELECT value FROM project_settings WHERE key = 'onboarded_at'").fetchone()
                    if row: onboarded_at = float(row['value'])
            except Exception: pass

            # 2. Check for Manual Seed Context
            has_seed = False
            try:
                with connect_db(ARCHEOLOGY_DB) as a_conn:
                    # Check if any parent directory or the file itself has a SEED_CONTEXT
                    seed_row = a_conn.execute(
                        "SELECT id FROM memory_archive WHERE type = 'SEED_CONTEXT' AND ? LIKE file_path || '%'",
                        (str(file_path),)
                    ).fetchone()
                    if seed_row: has_seed = True
            except Exception: pass

            # 3. Decision Logic: 
            # - Track Amnesia ONLY if modified AFTER onboarding.
            # - Seed context is for the initial baseline, but new changes MUST have tags.
            if mtime > onboarded_at:
                try:
                    with connect_db(ORCHESTRATION_DB) as o_conn:
                        o_conn.execute(
                            "INSERT INTO amnesia_log (timestamp, file_path, incident_report, type) VALUES (?, ?, ?, ?)",
                            (datetime.now(), str(file_path), "Missing @trace in post-onboarding modification", "DEFINITE")
                        )
                        o_conn.commit()
                except Exception: pass

        with connect_db(ARCHEOLOGY_DB) as conn:
            # --- SEMANTIC ARCHITECT (The HDC System) ---
            # Instead of raw code snapshots (which Git handles), we store 
            # ultra-lean Semantic Blueprints of the file's 'DNA'.
            main_feat = tags["traces"][0]["feat_id"] if tags["traces"] else "FEAT-UNKNOWN"
            
            blueprint_json = distiller.SemanticDistiller.distill(content, file_path.suffix)
            
            # Check if blueprint has changed to prevent redundant entries
            last_blueprint = conn.execute(
                "SELECT content_json FROM memory_archive WHERE file_path = ? AND type = 'SEMANTIC_BLUEPRINT' ORDER BY archived_at DESC LIMIT 1",
                (str(file_path),)
            ).fetchone()
            
            should_archive = True
            if last_blueprint and last_blueprint[0] == blueprint_json:
                should_archive = False

            if should_archive:
                archive.archive_record(
                    conn, "SEMANTIC_BLUEPRINT", main_feat, str(file_path), 
                    json.loads(blueprint_json),
                    f"Structural DNA captured at {datetime.now().strftime('%H:%M:%S')}",
                    magnitude=len(blueprint_json), sha=sha
                )

            # 1. Update Traces
            for trace in tags["traces"]:
                conn.execute("""
                    INSERT OR REPLACE INTO trace_matrix 
                    (feat_id, file_path, test_id, description, last_updated, line_count, size_bytes, git_sha, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
                """, (
                    trace["feat_id"], str(file_path), trace["test_id"], trace["desc"],
                    datetime.now(), len(content.splitlines()), len(content), sha
                ))
                updates += 1
                
            # 2. Update Decisions
            for dec in tags["decisions"]:
                tag_hash = archive.get_tag_hash(dec["feat_id"], dec["decision"], dec["rationale"])
                try:
                    conn.execute("""
                        INSERT INTO decision_log 
                        (feat_id, file_path, timestamp, decision, rationale, trade_offs, tag_hash, git_sha)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        dec["feat_id"], str(file_path), datetime.now(), 
                        dec["decision"], dec["rationale"], dec["trade_offs"], tag_hash, sha
                    ))
                    updates += 1
                except sqlite3.IntegrityError:
                    pass # Already logged this specific decision version
                    
            # 3. Update Stats
            if updates > 0:
                conn.execute("""
                    INSERT OR REPLACE INTO file_stats 
                    (file_path, change_count, last_size_bytes, last_updated, last_sha)
                    VALUES (?, (SELECT COALESCE(change_count, 0) + 1 FROM file_stats WHERE file_path = ?), ?, ?, ?)
                """, (str(file_path), str(file_path), len(content), datetime.now(), sha))
                
            conn.commit()
        return updates
    except Exception as e:
        logger.error(f"Failed to process {file_path}: {e}")
        return 0
