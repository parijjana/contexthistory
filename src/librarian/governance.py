import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from .db import connect_db, ARCHEOLOGY_DB, ORCHESTRATION_DB, PURGATORY_DB

logger = logging.getLogger("Librarian.Governance")

def generate_dashboard(workspace_root: str, supported_extensions: set) -> Dict[str, Any]:
    """Generates a high-density executive dashboard with analytics and parked logic."""
    try:
        with connect_db(ARCHEOLOGY_DB) as conn:
            # 1. CORE METRICS
            traces = conn.execute("SELECT COUNT(*) FROM trace_matrix WHERE status = 'ACTIVE'").fetchone()[0]
            decisions = conn.execute("SELECT COUNT(*) FROM decision_log").fetchone()[0]
            archive_count = conn.execute("SELECT COUNT(*) FROM memory_archive").fetchone()[0]
            
            # 2. PARKED LOGIC
            parked = conn.execute("SELECT feat_id, file_path, last_commit_msg, git_sha FROM trace_matrix WHERE status = 'PARKED'").fetchall()
            parked_count = len(parked)
            
            # 3. TRACE INTEGRITY
            total_files = 0
            for ext in supported_extensions:
                total_files += len(list(Path(workspace_root).rglob(f"*{ext}")))
            files_with_traces = conn.execute("SELECT COUNT(DISTINCT file_path) FROM trace_matrix WHERE status = 'ACTIVE'").fetchone()[0]
            integrity = int((files_with_traces / total_files * 100)) if total_files > 0 else 100

            # 4. SYNC TIMELINE
            syncs = conn.execute("SELECT timestamp, mode, items_updated FROM sync_history ORDER BY timestamp DESC LIMIT 10").fetchall()

        with connect_db(ORCHESTRATION_DB) as conn:
            # 5. TOOL EFFICACY (Telemetry)
            usage = conn.execute("SELECT tool_name, COUNT(*) as count FROM tool_usage_log GROUP BY tool_name ORDER BY count DESC").fetchall()
            amnesia_count = conn.execute("SELECT COUNT(*) FROM amnesia_log").fetchone()[0]
            amnesia_events = conn.execute("SELECT timestamp, incident_report, type FROM amnesia_log ORDER BY timestamp DESC LIMIT 5").fetchall()

        # HTML Generation
        sync_html = "".join([f'<div class="flex justify-between p-2 text-xs border-b"><span>{s["timestamp"]}</span><span class="font-bold">{s["mode"]}</span><span>{s["items_updated"]} updates</span></div>' for s in syncs]) or "No sync history."
        usage_html = "".join([f'<div class="flex justify-between p-2 text-xs border-b"><span>{u["tool_name"]}</span><span class="font-bold text-blue-600">{u["count"]} calls</span></div>' for u in usage]) or "No tool usage yet."
        parked_html = "".join([f'<div class="p-3 border-b bg-slate-50"><b>{p["feat_id"]}</b>: {p["file_path"]}<p class="text-xs text-slate-500 mt-1 italic">Last Git: "{p["last_commit_msg"]}"</p><code class="text-[10px] bg-slate-200 px-1">{p["git_sha"]}</code></div>' for p in parked]) or "No parked logic."
        amnesia_html = "".join([f'<div class="p-3 border-b {"text-red-700 bg-red-50" if i["type"]=="DEFINITE" else "text-orange-700 bg-orange-50"}"><b class="text-xs">[{i["type"]}] {i["timestamp"]}</b><p class="text-xs mt-1">{i["incident_report"]}</p></div>' for i in amnesia_events]) or "Perfect Recall."

        # Premium Aesthetics (Noise Texture & Gradient)
        noise_svg = '<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg"><filter id="n"><feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" stitchTiles="stitch"/></filter><rect width="100%" height="100%" filter="url(#n)" opacity="0.05"/></svg>'
        
        template = f"""<!DOCTYPE html>
<html lang="en"><head><script src="https://cdn.tailwindcss.com"></script>
<style>
    .noise {{ background-image: url('data:image/svg+xml;base64,{__import__("base64").b64encode(noise_svg.encode()).decode()}'); }}
    .glass {{ background: rgba(255, 255, 255, 0.8); backdrop-filter: blur(10px); }}
</style>
</head>
<body class="bg-slate-100 p-10 font-sans noise"><div class="max-w-7xl mx-auto">
    <div class="flex justify-between items-center mb-8">
        <div>
            <h1 class="text-3xl font-black text-slate-900 tracking-tighter">EVOLUTIONARY MEMORY <span class="text-blue-600">V7</span></h1>
            <p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Autonomous Quality Protocol</p>
        </div>
        <div class="flex gap-8">
            <div class="text-right"><p class="text-xs font-bold text-slate-400 uppercase">Context Load</p><p class="text-2xl font-black text-blue-600">Lean</p></div>
            <div class="text-right"><p class="text-xs font-bold text-slate-400 uppercase">System Integrity</p><p class="text-2xl font-black text-green-600">{integrity}%</p></div>
        </div>
    </div>

    <div class="grid grid-cols-4 gap-6 mb-8">
        <div class="bg-white/80 glass p-6 rounded-2xl shadow-xl border-b-4 border-blue-500"><p class="text-xs font-bold text-slate-400 uppercase mb-1">Decisions</p><p class="text-4xl font-black text-slate-800">{decisions}</p></div>
        <div class="bg-white/80 glass p-6 rounded-2xl shadow-xl border-b-4 border-indigo-500"><p class="text-xs font-bold text-slate-400 uppercase mb-1">Archive Density</p><p class="text-4xl font-black text-slate-800">{archive_count}</p></div>
        <div class="bg-white/80 glass p-6 rounded-2xl shadow-xl border-b-4 border-orange-500"><p class="text-xs font-bold text-slate-400 uppercase mb-1">Parked Logic</p><p class="text-4xl font-black text-slate-800">{parked_count}</p></div>
        <div class="bg-white/80 glass p-6 rounded-2xl shadow-xl border-b-4 border-red-500"><p class="text-xs font-bold text-slate-400 uppercase mb-1">Amnesia Events</p><p class="text-4xl font-black text-slate-800">{amnesia_count}</p></div>
    </div>

    <div class="grid grid-cols-3 gap-8">
        <div class="space-y-8">
            <div class="bg-white/80 glass rounded-2xl shadow-lg overflow-hidden border"><div class="p-4 border-b bg-slate-50/50 font-black text-xs uppercase tracking-wider">Sync Timeline</div><div class="p-2">{sync_html}</div></div>
            <div class="bg-white/80 glass rounded-2xl shadow-lg overflow-hidden border"><div class="p-4 border-b bg-slate-50/50 font-black text-xs uppercase tracking-wider">Tool Efficacy</div><div class="p-2">{usage_html}</div></div>
        </div>
        <div class="bg-white/80 glass rounded-2xl shadow-lg overflow-hidden border col-span-1"><div class="p-4 border-b bg-orange-50/50 font-black text-xs uppercase tracking-wider text-orange-700">Parked Logic (Reinstatement Ready)</div><div>{parked_html}</div></div>
        <div class="bg-white/80 glass rounded-2xl shadow-lg overflow-hidden border col-span-1"><div class="p-4 border-b bg-red-50/50 font-black text-xs uppercase tracking-wider text-red-700">Amnesia Audit</div><div>{amnesia_html}</div></div>
    </div>
    
    <div class="mt-8 text-center"><p class="text-[10px] text-slate-400 font-medium uppercase tracking-[0.2em]">Generated by Librarian Worker • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p></div>
</div></body></html>"""

        dashboard_path = os.path.join(workspace_root, "dashboard.html")
        with open(dashboard_path, "w", encoding="utf-8") as f: f.write(template)
        return {"status": "DASHBOARD_READY", "path": dashboard_path}
    except Exception as e:
        logger.error(f"Dashboard Failed: {e}"); return {"status": "ERROR", "message": str(e)}

def get_text_summary(workspace_root: str, supported_extensions: set) -> str:
    """Generates a high-signal text summary for terminal display."""
    try:
        with connect_db(ARCHEOLOGY_DB) as conn:
            traces = conn.execute("SELECT COUNT(*) FROM trace_matrix WHERE status = 'ACTIVE'").fetchone()[0]
            decisions = conn.execute("SELECT COUNT(*) FROM decision_log").fetchone()[0]
            archive_count = conn.execute("SELECT COUNT(*) FROM memory_archive").fetchone()[0]
            parked_count = conn.execute("SELECT COUNT(*) FROM trace_matrix WHERE status = 'PARKED'").fetchone()[0]
            total_files = 0
            for ext in supported_extensions: total_files += len(list(Path(workspace_root).rglob(f"*{ext}")))
            files_with_traces = conn.execute("SELECT COUNT(DISTINCT file_path) FROM trace_matrix WHERE status = 'ACTIVE'").fetchone()[0]
            integrity = int((files_with_traces / total_files * 100)) if total_files > 0 else 100
        with connect_db(ORCHESTRATION_DB) as conn:
            amnesia_count = conn.execute("SELECT COUNT(*) FROM amnesia_log").fetchone()[0]
        
        return f"=== MEMORY V7 ===\nDecisions: {decisions} | History: {archive_count}\nIntegrity: {integrity}% | Parked: {parked_count}\nAmnesia Alerts: {amnesia_count}"
    except Exception as e: return f"ERROR: {e}"
