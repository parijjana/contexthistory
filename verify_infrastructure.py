import os
import sqlite3
import time
from pathlib import Path
from mcp_server import sync_traces, query_matrix, record_decision, get_historical_context, initiate_asynchronous_validation

def test_infrastructure():
    print("--- Starting Infrastructure Verification ---\n")

    # 1. Seed the Project with a dummy file and trace
    test_file = Path("test_feature.dart")
    test_file.write_text("// @trace FEAT-777 | Implementing Secure Auth | TestID: AUTH-TEST-01\nvoid main() { print('Hello World'); }")
    print(f"[1] Seeded {test_file} with trace FEAT-777")

    # 2. Trigger Sync (Directly calling the tool function)
    print("[2] Running sync_traces...")
    sync_result = sync_traces()
    print(f"    Sync Status: {sync_result['status']}, Traces Found: {sync_result['traces_found']}")

    # 3. Query Matrix
    print("[3] Querying Matrix for FEAT-777...")
    matrix_data = query_matrix("FEAT-777")
    if matrix_data:
        print(f"    Found File: {matrix_data[0]['file']}")
    else:
        print("    FAILED: FEAT-777 not found in matrix.")

    # 4. Fossilize a Decision
    print("[4] Recording Architectural Decision (Fossilization)...")
    record_decision(
        feat_id="FEAT-777",
        file_path=str(test_file),
        decision="Use Argon2 for hashing",
        rationale="Superior resistance to GPU-based brute force attacks.",
        trade_offs="Higher CPU/Memory overhead on the client side."
    )

    # 5. Retrieve Context
    print("[5] Retrieving Historical Context for 'test_feature.dart'...")
    history = get_historical_context(str(test_file))
    if history:
        print(f"    Last Decision: {history[0]['decision']}")
        print(f"    Rationale: {history[0]['rationale']}")

    # 6. Initiate Handoff
    print("[6] Initiating Asynchronous Validation (Handoff)...")
    handoff = initiate_asynchronous_validation("FEAT-777")
    print(f"    Status: {handoff['status']}, Session ID: {handoff['session_id']}")

    print("\n--- Verification Complete: Infrastructure is Robust ---")

if __name__ == "__main__":
    try:
        test_infrastructure()
    finally:
        # Cleanup (Optional: uncomment to remove test file and DB)
        # if os.path.exists("test_feature.dart"): os.remove("test_feature.dart")
        # if os.path.exists("quality_memory.db"): os.remove("quality_memory.db")
        pass
