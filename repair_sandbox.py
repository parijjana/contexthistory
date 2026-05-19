import os
import sys
import time

# Add src to path
sys.path.append(os.path.abspath("evolutionary-test-sandbox/evolutionary-memory/src"))

from librarian import db, discovery, worker

WORKSPACE_ROOT = "evolutionary-test-sandbox"
os.environ["WORKSPACE_ROOT"] = WORKSPACE_ROOT

def manual_sync():
    print(f"Changing directory to {WORKSPACE_ROOT}...")
    os.chdir(WORKSPACE_ROOT)
    
    # Refresh Workspace Root for discovery
    import librarian.discovery
    import librarian.db
    import librarian.worker
    
    print("Initializing databases...")
    librarian.db.init_db()
    
    print("Starting manual sync...")
    config = librarian.discovery.load_config(".")
    ignore_spec = librarian.discovery.get_ignore_spec(".")
    
    # Force full scan by setting last_sync to 0
    last_sync_time = 0
    current_run_time = time.time()
    current_sha = librarian.discovery.get_current_sha(".")
    
    delta_paths = librarian.discovery.get_delta_files(".", ignore_spec)
    print(f"Found {len(delta_paths)} files to process.")
    
    updates = 0
    for path in delta_paths:
        updates += librarian.worker.process_file(path, last_sync_time, current_run_time, 10, current_sha, config)
    
    librarian.worker.log_sync_event("MANUAL_REPAIR", len(delta_paths), updates)
    print(f"Sync complete: {updates} updates.")

if __name__ == "__main__":
    manual_sync()
