import sqlite3
import time
import os
from pathlib import Path
from datetime import datetime
from src.librarian import db, worker, discovery

def test_onboarding_and_amnesia():
    print("🧪 Starting Empirical Validation of Onboarding & Amnesia Logic...")
    
    # 1. Clean/Init DBs for testing
    db.init_db()
    
    # Setup test file
    test_file = Path("legacy_test.py")
    test_file.write_text("def legacy_func(): pass")
    
    # 2. Set Onboarding Checkpoint (Simulation)
    # We set it to 'now'
    onboard_time = time.time()
    with db.connect_db(db.ORCHESTRATION_DB) as conn:
        conn.execute("INSERT OR REPLACE INTO project_settings (key, value, last_updated) VALUES (?, ?, ?)",
                   ("onboarded_at", str(onboard_time), datetime.now()))
        conn.commit()
    print(f"✅ Onboarding checkpoint set at: {onboard_time}")

    # 3. Test Legacy File (Pre-onboarding/Unchanged)
    # Simulate a file existing before onboarding by setting its mtime back
    os.utime(test_file, (onboard_time - 100, onboard_time - 100))
    
    config = discovery.load_config(".")
    # process_file should NOT trigger amnesia because mtime < onboard_time
    worker.process_file(test_file, 0, time.time(), 1, "TEST-SHA", config)
    
    with db.connect_db(db.ORCHESTRATION_DB) as conn:
        row = conn.execute("SELECT COUNT(*) as count FROM amnesia_log WHERE file_path = ?", (str(test_file),)).fetchone()
        if row['count'] == 0:
            print("✅ PASS: Legacy file (unchanged) did NOT trigger amnesia.")
        else:
            print("❌ FAIL: Legacy file triggered amnesia unexpectedly.")

    # 4. Test Post-Onboarding Modification (Missing Traces)
    time.sleep(1.1) # Ensure mtime is strictly greater
    test_file.write_text("def modified_func(): pass # No traces here")
    # Current mtime will be > onboard_time
    
    worker.process_file(test_file, 0, time.time(), 1, "TEST-SHA", config)
    
    with db.connect_db(db.ORCHESTRATION_DB) as conn:
        row = conn.execute("SELECT COUNT(*) as count FROM amnesia_log WHERE file_path = ?", (str(test_file),)).fetchone()
        if row['count'] > 0:
            print("✅ PASS: Post-onboarding modification (missing traces) TRIGGERED amnesia.")
        else:
            print("❌ FAIL: Post-onboarding modification failed to trigger amnesia.")

    # 5. Cleanup
    if test_file.exists(): os.remove(test_file)

if __name__ == "__main__":
    test_onboarding_and_amnesia()
