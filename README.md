# Evolutionary Memory 🧠

An intelligent, context-aware memory system for Gemini CLI. This extension allows agents to "remember" patterns, architectural decisions, and project evolution across sessions using a local MCP server and a specialized Skill.

## 🚀 Quick Start

### 1. Installation
Install the extension directly via the Gemini CLI:

```bash
gemini extensions install https://github.com/parijjana/contexthistory
```

### 2. Setup Prerequisites
The memory engine runs on Python. Ensure you have the dependencies installed:

```bash
pip install -r requirements.txt
```

### 3. Initialize & Trust
Open a Gemini CLI session in your project and trust the new extension:

```bash
/trust
```

## 🛠️ Features

- **Context Archeology:** Automatically recovers relevant history from previous sessions.
- **Semantic Distillation:** Compresses verbose logs into actionable architectural insights.
- **Pattern Recognition:** Identifies recurring bugs or engineering preferences.
- **MCP Integration:** Provides tools for querying and updating memory databases locally.

## 📖 Usage

Once installed, your agent will automatically identify when to use the Evolutionary Memory skill based on your prompts. You can also manually trigger it:

- *"Check the evolutionary memory for our previous decisions on database schema."*
- *"Distill the last 3 sessions into our ARCHITECTURE.md."*
- *"What patterns are we seeing in our recent test failures?"*

## 📂 Structure

- `SKILL.md`: The "Instruction Set" that guides the agent on how to use the memory.
- `gemini-extension.json`: Manifest file for CLI integration.
- `src/mcp_server.py`: The Python-based MCP server providing the memory tools.
- `src/librarian/`: Core logic for parsing, archiving, and distilling project history.

## 🔌 Cross-Agent Support (Claude, Cursor, etc.)

Since the core of this project is a standard **Model Context Protocol (MCP)** server, you can use these tools with other compatible agents like Claude Desktop or Cursor.

### Automated Setup (Claude Desktop)

We provide a script to automatically configure Claude Desktop for you:

```bash
python setup_agents.py
```
*This script will install dependencies and inject the MCP server configuration into your Claude settings.*

### Manual Setup for Claude Desktop

1. Open your Claude Desktop configuration file:
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
   - **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

2. Add the following entry to the `mcpServers` list:

```json
{
  "mcpServers": {
    "evolutionary-memory": {
      "command": "python",
      "args": ["-u", "C:/PATH/TO/contexthistory/src/mcp_server.py"],
      "env": {
        "PYTHONPATH": "C:/PATH/TO/contexthistory"
      }
    }
  }
}
```
*(Replace `C:/PATH/TO/` with the actual absolute path to your cloned repository.)*

---

## 🤝 Contributing

This project is in active development. If you'd like to help "iron out" the memory logic:
1. Fork the repo.
2. Create a feature branch.
3. Submit a Pull Request.

---
*Created with 🦾 by Gemini CLI*
