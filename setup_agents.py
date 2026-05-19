import os
import sys
import json
import platform
import subprocess
from pathlib import Path

def get_claude_config_path():
    """Returns the platform-specific path to the Claude Desktop config."""
    home = Path.home()
    if platform.system() == "Windows":
        return home / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
    elif platform.system() == "Darwin":  # macOS
        return home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    else:
        return None

def setup_claude():
    print("🔧 Setting up Evolutionary Memory for Claude Desktop...")
    
    config_path = get_claude_config_path()
    if not config_path:
        print("❌ Error: Unsupported operating system for automatic Claude setup.")
        return

    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing config or create new
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except json.JSONDecodeError:
            print("⚠️ Warning: Existing config is invalid JSON. Creating a fresh one.")
            config = {}
    else:
        config = {}

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    # Get absolute paths
    root_dir = Path(__file__).parent.absolute()
    server_path = root_dir / "src" / "mcp_server.py"
    
    if not server_path.exists():
        print(f"❌ Error: MCP server file not found at {server_path}")
        return

    # Prepare configuration entry
    python_cmd = "python" if platform.system() == "Windows" else "python3"
    
    config["mcpServers"]["evolutionary-memory"] = {
        "command": python_cmd,
        "args": ["-u", str(server_path)],
        "env": {
            "PYTHONPATH": str(root_dir)
        }
    }

    # Save config
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"✅ Successfully updated Claude config at: {config_path}")
    except Exception as e:
        print(f"❌ Error writing config: {e}")

def install_dependencies():
    print("📦 Installing Python dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully.")
    except Exception as e:
        print(f"❌ Error installing dependencies: {e}")

def main():
    print("--- Evolutionary Memory Setup ---")
    
    # 1. Install dependencies
    install_dependencies()
    
    # 2. Setup Claude
    setup_claude()
    
    print("\n🎉 Setup complete! Please restart Claude Desktop to enable the new tools.")

if __name__ == "__main__":
    main()
