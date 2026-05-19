import os
import sqlite3
import time
import subprocess
import json
import re
import sys
import traceback
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

# Modular Imports
from librarian import db, discovery

# Security & Validation
TEST_ID_REGEX = re.compile(r"^TEST-\d{8}-\d{6}-\d{4}$", re.IGNORECASE)
LAUNCHER_FOLDER = ".librarian"
LAUNCHER_NAME = "test_launcher.sh" if os.name != "nt" else "test_launcher.ps1"

def extract_snippet(text: str, lines: int = 20) -> str:
    if not text: return ""
    line_list = text.strip().splitlines()
    return "\n".join(line_list[-lines:])

def cleanup_stale_reports(feat_id: str, current_session_id: str):
    """Deletes summaries and logs from previous sessions for the same feature."""
    try:
        with db.connect_db(db.ORCHESTRATION_DB) as conn:
            cursor = conn.execute("SELECT session_id, summary_path FROM validation_history WHERE feat_id = ? AND session_id != ?", (feat_id, current_session_id))
            for row in cursor.fetchall():
                if row['summary_path'] and os.path.exists(row['summary_path']):
                    try: os.remove(row['summary_path'])
                    except Exception: pass
                ldir = Path("agent_log") / row['session_id']
                if ldir.exists():
                    try: shutil.rmtree(ldir)
                    except Exception: pass
    except Exception: pass

def run_single_test(file_path_str: str, test_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Executes a test using Agnostic Runner Registry."""
    if not TEST_ID_REGEX.match(test_id): return {"status": "ERROR", "message": "Invalid Test ID format."}
    
    file_path = Path(file_path_str)
    logical_root = discovery.find_logical_root(file_path) if hasattr(discovery, 'find_logical_root') else Path(".")
    launcher_path = logical_root / LAUNCHER_FOLDER / LAUNCHER_NAME
    ext = file_path.suffix
    
    try:
        # STRATEGY A: Custom Launcher
        if launcher_path.exists():
            cmd = [str(launcher_path), test_id]
            if os.name != "nt": os.chmod(launcher_path, 0o755)
        # STRATEGY B: Agnostic Runner Registry (from config)
        elif ext in config.get("runners", {}):
            runner = config["runners"][ext]
            cmd = runner["cmd"] + [test_id]
        else:
            return {"status": "UNSUPPORTED", "message": f"No runner defined for {ext} in .librarian/config.json"}

        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=60, 
            cwd=str(logical_root),
            shell=(os.name == "nt"), # Essential for finding binaries in PATH on Windows
            env=os.environ.copy()    # Ensure current PATH and other env vars are inherited
        )
        full_output = f"{result.stdout}\n{result.stderr}"
        is_passed = result.returncode == 0
        
        # Zero-Test Check
        zero_pattern = config.get("runners", {}).get(ext, {}).get("zero_pattern", "")
        if zero_pattern and re.search(zero_pattern, full_output, re.I):
            return {"status": "FAILURE", "reason": "ZERO_TESTS_DETECTED", "output": extract_snippet(full_output)}

        return {
            "status": "SUCCESS" if is_passed else "FAILURE",
            "output": full_output if not is_passed else "",
            "snippet": extract_snippet(full_output) if not is_passed else ""
        }
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}

def run_tests(session_id, feat_id):
    """Asynchronous Feature Validation Entry Point."""
    config = discovery.load_config(".")
    with db.connect_db(db.ARCHEOLOGY_DB) as conn:
        cursor = conn.execute("SELECT file_path, test_id FROM trace_matrix WHERE feat_id = ?", (feat_id,))
        targets = cursor.fetchall()
    
    summary_path = f"VALIDATION_SUMMARY_{session_id}.md"
    log_dir = Path("agent_log") / session_id
    log_dir.mkdir(parents=True, exist_ok=True)
    
    test_results, all_passed = [], True
    for row in targets:
        res = run_single_test(row['file_path'], row['test_id'], config)
        passed = res['status'] == "SUCCESS"
        if not passed: 
            all_passed = False
            log_path = log_dir / f"{row['test_id']}.log"
            with open(log_path, "w", encoding="utf-8") as lf: lf.write(res.get('output', ''))
        
        test_results.append({
            "tid": row['test_id'], "file": row['file_path'], "status": res['status'], 
            "reason": res.get('reason', ''), "snippet": res.get('snippet', ''), 
            "log_ref": f"{log_dir}/{row['test_id']}.log" if not passed else None
        })

    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(f"# Forensic Validation: {feat_id}\n- **Result:** {'✅ SUCCESS' if all_passed else '❌ FAILURE'}\n\n")
        for t in test_results:
            f.write(f"### {'✅' if t['status']=='SUCCESS' else '❌'} {t['tid']}\n")
            if t['status'] != "SUCCESS":
                f.write(f"- **Log:** [{t['tid']}.log]({t['log_ref']})\n```text\n{t['snippet']}\n```\n")
        
    if all_passed and log_dir.exists(): shutil.rmtree(log_dir)
    cleanup_stale_reports(feat_id, session_id)

    with db.connect_db(db.ORCHESTRATION_DB) as conn:
        conn.execute("UPDATE validation_history SET status = ?, t_end = ?, summary_path = ? WHERE session_id = ?", 
                   ("SUCCESS" if all_passed else "FAILURE", datetime.now(), summary_path, session_id))
        conn.commit()

if __name__ == "__main__":
    if len(sys.argv) >= 3: run_tests(sys.argv[1], sys.argv[2])
