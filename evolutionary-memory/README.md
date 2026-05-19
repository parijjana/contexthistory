# 🧠 Skill: Evolutionary Memory & Autonomous Quality

Stop project "Contextual Arthritis." This skill allows Gemini CLI to manage multi-year projects by offloading architectural rationale and file mapping to a persistent SQLite "Librarian."

## 🚀 Why Use This?
Standard LLM sessions suffer from "Amnesia." Once the context window fills up, the agent forgets *why* it wrote code a certain way. This skill creates **Decision Fossils**—persistent, searchable rationales that any future agent can query instantly.

## 📦 Installation

1. **Clone the Skill:**
   Copy these files into your project or a central `skills/` folder:
   - `mcp_server.py` (The Librarian)
   - `inspector.py` (The Background Validator)
   - `requirements.txt`
   - `SKILL.md` (The SOP)

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Register the MCP Server:**
   Add this to your `~/.gemini/settings.json`:
   ```json
   {
     "mcpServers": {
       "memory": {
         "command": "python",
         "args": ["/path/to/mcp_server.py"]
       }
     }
   }
   ```

## 🛠 Usage Workflow

### Step 1: Initialize (Grounding)
In a new project, tell the agent:
> "Sync project traces and check the matrix."

### Step 2: Implementation (Traceability)
The agent will automatically tag edits:
```python
# @trace FEAT-101 | Implement OAuth | TestID: AUTH-01
def login(): ...
```

### Step 3: Fossilization (The 'Why')
When you make a critical choice, the agent records it:
> "Record decision: Using Redis for session storage to handle horizontal scaling."

### Step 4: The Handoff (Efficiency)
To save money and tokens, use the handoff:
> "Save state for FEAT-101 and trigger background validation."
*The agent will save a 50-token 'Telegram' and exit, letting `inspector.py` run tests in the background.*

## 📊 Dashboard
Run the `generate_health_report` tool to see your **Trace Integrity** and **Memory Density** in a beautiful Tailwind dashboard (`dashboard.html`).

---
*Built for the Gemini CLI Topic Model.*
