# Skill: Autonomous Quality & Evolutionary Memory

This skill enables an agent to manage large-scale projects without context bloat by offloading history and traceability to an external SQLite database.

## Core Philosophy (Pragmatic Feature-First)
1. **Outcome > Aesthetics:** Behavioral correctness (it works) is the only metric that matters.
2. **Tri-Tier Verification:** Validate via Automated Tests, User Feedback, and Performance Audits.
3. **High-Signal Context:** Keep history concise. Functional clarity is superior to granular perfection.
4. **Feature-First:** Track Product Features, not code granularity.

## System Prerequisites
- Python 3.10+
- SQLite3
- Gemini CLI with MCP support

## User Setup
1. **Clone/Copy:** Place the `evolutionary-memory/` directory in your workspace.
2. **Install:** Run `pip install -r requirements.txt`.
3. **Register:** Add the following to your `~/.gemini/settings.json`:
   ```json
   {
     "mcpServers": {
       "memory": {
         "command": "python",
         "args": ["path/to/evolutionary-memory/src/mcp_server.py"]
       }
     }
   }
   ```

## Agent Workflows

### 1. Phase 0: Project Onboarding & Genesis Mapping
When starting with an existing ("in-flight") project, you must establish a "Day Zero" memory baseline to ground your future work.

1.  **Initiate Onboarding:** Call `onboard_project()`. This will generate a comprehensive map of the current source files and tests.
2.  **Interactive Seeding (Human-Gated):** Inform the user that evolutionary history begins from this point. Then, conduct a guided "Interview" for each major module in the map:
    - Ask the user: *"For the module `[directory]`, should I analyze the files to propose a context, or would you like to provide it manually?"*
    - **If Agent Analysis is chosen:** Read the files in that directory, summarize their core intent and architectural role, and present this to the user for confirmation.
    - **If Manual Seeding is chosen:** Ask the user to describe the module's purpose.
    - Call `seed_initial_context(module_path, context)` once the context is finalized.
    - *Repeat* this for all major modules until the user is satisfied.
3.  **Genesis Marking:** This process marks the transition from "untracked legacy" to "evolutionary tracked" code.

### 2. Teaching the Librarian (Configuration)
You can "Teach" the Librarian new language patterns and test runners by updating the project-level config.
- **Location:** `.librarian/config.json`
- **Capabilities:**
  - **`ext_markers`**: Anchored regex to identify "Logic" for specific extensions.
  - **`runners`**: Platform-agnostic execution patterns (commands, zero-test detection).
- **Example:**
```json
{
  "runners": {
    ".rs": {
      "cmd": ["cargo", "test", "--"],
      "zero_pattern": "0 tests completed"
    }
  }
}
```

### 2. Verification Environment Setup
If the project requires a specific environment (venv, node_modules, monorepo paths), you **MUST** create a custom test launcher. 
- **Location:** `.librarian/test_launcher.sh` (or `.ps1`) in the project root.
- **Contract:** The script must accept the `test_id` as the first argument (`$1`).

### 3. Implementation (The Birth of a Feature)
If starting a new task, **auto-generate the `feat_id`** using the current timestamp and a 4-digit session suffix:
Format: `FEAT-YYYYMMDD-HHMMSS-NNNN`.

### 4. Unified Tagging (Identity Headers)
To minimize code clutter, **MUST** group all `@trace` and `@decision` tags into an **Identity Header** at the top of the file or logical block. Use **YAML-Fossil** format.

**Example:**
```python
# @trace FEAT-20260512-143005-0000
# Description: Modular authentication engine.
# TestID: TEST-20260512-143005-0001
#
# @decision FEAT-20260512-143005-0000
# Decision: Argon2 Hashing
# Rationale: Standard for high-security data.
```

### 5. Verification (Active Coding)
Use `validate_test_case(test_id)` to run individual tests synchronously.

### 6. The Handoff (Token Flush & Lean Resumption)
When your session tokens are high or a task is complete:
1. **MANDATORY:** Call `trigger_sync()` to wake the Librarian (Fire-and-Forget).
2. Call `record_handoff_state(feat_id, status, pending_tasks)` to save session state.
3. Call `initiate_asynchronous_validation(feat_id)` to trigger background tests.
4. **Terminate session immediately.**

### 7. Resumption (New Session)
1. Call `get_handoff_state(feat_id)` to rehydrate.
2. Call `get_validation_status(session_id)` to check background results.
3. Call `get_file_evolution(file_path)` to understand recent change magnitude.

## Evolutionary Memory Design
This skill prevents "Contextual Arthritis" by ensuring that 2-year-old history is only retrieved **on-demand**.
