import os
import threading
import logging
import json
import time
from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP

# Modular Imports
from librarian import db, discovery, governance, worker, distributed

# Configure registry-safe logging
log_file = os.path.join(os.getcwd(), 'memory_librarian.log')
logging.basicConfig(
    level=logging.INFO,
    filename=log_file,
    filemode='a',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Librarian.MCP")

mcp = FastMCP("AutonomousQualityServer")
WORKSPACE_ROOT = os.environ.get("WORKSPACE_ROOT", ".")
sync_trigger = threading.Event()

def log_tool_usage(tool_name: str, feat_id: str = "N/A", status: str = "SUCCESS"):
    """Internal helper to track tool efficacy."""
    try:
        with db.connect_db(db.ORCHESTRATION_DB) as conn:
            conn.execute("INSERT INTO tool_usage_log (timestamp, tool_name, feat_id, result_status) VALUES (?, ?, ?, ?)",
                       (__import__('datetime').datetime.now(), tool_name, feat_id, status))
            conn.commit()
    except Exception: pass

def run_background_crawler(interval: int = 1800):
    """Adaptive background crawler loop with Purgatory and Distributed Memory support."""
    last_sync_time = 0
    while True:
        sync_trigger.wait(timeout=interval)
        sync_trigger.clear()
        try:
            config = discovery.load_config(WORKSPACE_ROOT)
            ignore_spec = discovery.get_ignore_spec(WORKSPACE_ROOT)
            
            # 1. Team Sync & Purgatory Reconciliation
            if config.get("enable_distributed_memory", False): distributed.import_memory(WORKSPACE_ROOT)
            worker.reconcile_purgatory(WORKSPACE_ROOT, ignore_spec)
            
            current_run_time, current_sha = time.time(), discovery.get_current_sha(WORKSPACE_ROOT)
            delta_paths = discovery.get_delta_files(WORKSPACE_ROOT, ignore_spec)
            
            updates = 0
            for path in delta_paths:
                updates += worker.process_file(path, last_sync_time, current_run_time, 10, current_sha, config)
            
            # 2. Distributed Memory Export
            if updates > 0 and config.get("enable_distributed_memory", False): distributed.export_memory(WORKSPACE_ROOT, current_sha)

            # 3. Log Sync Event for Timeline
            worker.log_sync_event("AUTO" if not sync_trigger.is_set() else "MANUAL", len(delta_paths), updates)
            
            if updates > 0: logger.info(f"Crawl complete: {updates} updates.")
            last_sync_time = current_run_time
        except Exception as e: logger.error(f"Crawler failure: {e}")

@mcp.tool()
def trigger_sync() -> Dict[str, str]:
    """Wakes Librarian for an immediate adaptive crawl."""
    log_tool_usage("trigger_sync")
    sync_trigger.set()
    return {"status": "SYNC_TRIGGERED"}

@mcp.tool()
def query_matrix(feat_id: str) -> Dict[str, Any]:
    """Query Trace Matrix for a specific feature."""
    log_tool_usage("query_matrix", feat_id)
    try:
        with db.connect_db(db.ARCHEOLOGY_DB) as conn:
            query = "SELECT feat_id, file_path, test_id, description, status, last_commit_msg FROM trace_matrix WHERE feat_id = ?"
            rows = conn.execute(query, (feat_id,)).fetchall()
            return {"status": "SUCCESS", "data": [dict(row) for row in rows]}
    except Exception as e: return {"status": "ERROR", "message": str(e)}

@mcp.tool()
def get_historical_context(file_path: str, limit: int = 5) -> Dict[str, Any]:
    """Retrieve high-density structural DNA and decision fossils for a file."""
    log_tool_usage("get_historical_context")
    try:
        with db.connect_db(db.ARCHEOLOGY_DB) as conn:
            # 1. Get Decisions
            d_query = "SELECT timestamp, decision, rationale, trade_offs, git_sha FROM decision_log WHERE file_path = ? ORDER BY timestamp DESC LIMIT ?"
            decisions = [dict(row) for row in conn.execute(d_query, (file_path, limit)).fetchall()]
            
            # 2. Get Blueprints (DNA)
            b_query = "SELECT archived_at, content_json, reason FROM memory_archive WHERE file_path = ? AND type = 'SEMANTIC_BLUEPRINT' ORDER BY archived_at DESC LIMIT ?"
            blueprints = []
            for row in conn.execute(b_query, (file_path, limit)).fetchall():
                blueprints.append({
                    "timestamp": row['archived_at'],
                    "dna": json.loads(row['content_json']),
                    "context": row['reason']
                })
                
            return {
                "status": "SUCCESS", 
                "decisions": decisions,
                "blueprints": blueprints
            }
    except Exception as e: return {"status": "ERROR", "message": str(e)}

@mcp.tool()
def get_semantic_blueprint(feat_id: str) -> Dict[str, Any]:
    """Retrieves high-density structural blueprints for a specific feature."""
    log_tool_usage("get_semantic_blueprint", feat_id)
    try:
        with db.connect_db(db.ARCHEOLOGY_DB) as conn:
            cursor = conn.execute("""
                SELECT file_path, content_json, archived_at, reason 
                FROM memory_archive 
                WHERE feat_id = ? AND type = 'SEMANTIC_BLUEPRINT'
                ORDER BY archived_at DESC
            """, (feat_id,))
            rows = cursor.fetchall()
            
            blueprints = []
            seen_files = set()
            for row in rows:
                if row['file_path'] not in seen_files:
                    blueprints.append({
                        "file": row['file_path'],
                        "blueprint": json.loads(row['content_json']),
                        "timestamp": row['archived_at'],
                        "context": row['reason']
                    })
                    seen_files.add(row['file_path'])
                    
            return {"status": "SUCCESS", "blueprints": blueprints}
    except Exception as e: return {"status": "ERROR", "message": str(e)}

@mcp.tool()
def generate_health_report() -> Dict[str, Any]:
    """Generates the high-density dashboard.html."""
    log_tool_usage("generate_health_report")
    return governance.generate_dashboard(WORKSPACE_ROOT, discovery.SUPPORTED_EXTENSIONS)

@mcp.tool()
def get_health_summary() -> str:
    """Terminal-friendly project health summary."""
    log_tool_usage("get_health_summary")
    return governance.get_text_summary(WORKSPACE_ROOT, discovery.SUPPORTED_EXTENSIONS)

@mcp.tool()
def get_memory_archive(file_path: Optional[str] = None, limit: int = 10, offset: int = 0, rank_by: str = "recency") -> Dict[str, Any]:
    """Paginated retrieval of archived fossils."""
    log_tool_usage("get_memory_archive")
    try:
        order = "archived_at" if rank_by == "recency" else "magnitude"
        with db.connect_db(db.ARCHEOLOGY_DB) as conn:
            base_q = "SELECT archived_at, type, feat_id, file_path, reason, magnitude, git_sha FROM memory_archive"
            if file_path:
                q = f"{base_q} WHERE file_path = ? ORDER BY {order} DESC LIMIT ? OFFSET ?"
                params = (file_path, limit, offset)
            else:
                q = f"{base_q} ORDER BY {order} DESC LIMIT ? OFFSET ?"
                params = (limit, offset)
            return {"status": "SUCCESS", "data": [dict(row) for row in conn.execute(q, params).fetchall()]}
    except Exception as e: return {"status": "ERROR", "message": str(e)}

def main():
    db.init_db()
    threading.Thread(target=run_background_crawler, daemon=True).start()
    mcp.run()

if __name__ == "__main__":
    main()
