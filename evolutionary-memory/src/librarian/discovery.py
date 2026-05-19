import os
import subprocess
import pathspec
import logging
import json
import re
from pathlib import Path
from typing import Set, Dict, Any

logger = logging.getLogger("Librarian.Discovery")

# --- GLOBAL FACTORY DEFAULTS ---
DEFAULT_EXT_MARKERS = {
    ".py": [r"^def\s+\w+", r"^class\s+\w+", r"^@\w+"],
    ".dart": [r"\w+\s+\w+\(.*\)\s*{", r"class\s+\w+", r"void\s+\w+", r"Future<"],
    ".js": [r"function\s+\w+", r"const\s+\w+\s*=\s*\(.*\)\s*=>", r"class\s+\w+"],
    ".ts": [r"function\s+\w+", r"const\s+\w+\s*=\s*\(.*\)\s*=>", r"class\s+\w+", r"interface\s+\w+"],
}

DEFAULT_RUNNERS = {
    ".py": {"cmd": ["pytest", "-k"], "zero_pattern": r"collected 0 items"},
    ".dart": {"cmd": ["flutter", "test", "--plain-name"], "zero_pattern": r"0 tests passed"},
    ".js": {"cmd": ["npm", "test", "--", "-t"], "zero_pattern": r"Test Suites: 0 passed, 0 total"}
}

SUPPORTED_EXTENSIONS = {".dart", ".py", ".js", ".ts", ".go", ".rs", ".java", ".cpp", ".sql"}
PRUNE_DIRS = {".git", "build", "dist", "node_modules", ".dart_tool", "__pycache__", ".memory", "evolutionary-memory"}
PROJECT_MARKERS = ["pubspec.yaml", "package.json", "pyproject.toml", "requirements.txt", ".git", "go.mod", "Cargo.toml"]
LAUNCHER_FOLDER = ".librarian"
LAUNCHER_NAME = "test_launcher.sh" if os.name != "nt" else "test_launcher.ps1"

def find_logical_root(file_path: Path) -> Path:
    """Traverses up from file_path to find the nearest project root marker."""
    current = file_path.parent
    while current != current.parent:
        if any((current / marker).exists() for marker in PROJECT_MARKERS): return current
        if (current / LAUNCHER_FOLDER / LAUNCHER_NAME).exists(): return current
        current = current.parent
    return Path(".")

def load_config(workspace_root: str) -> Dict[str, Any]:
    """Unified Config Loader for Librarian and Inspector."""
    config = {
        "ext_markers": DEFAULT_EXT_MARKERS,
        "runners": DEFAULT_RUNNERS,
        "always_logic": [".yaml", ".yml", ".toml"],
        "suppress_amnesia": False,
        "enable_distributed_memory": False, # New: Toggle for Git-backed team sync
    }
    config_path = Path(workspace_root) / ".librarian" / "config.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
                # Deep merge logic
                if "ext_markers" in user_config: config["ext_markers"].update(user_config["ext_markers"])
                if "runners" in user_config: config["runners"].update(user_config["runners"])
                if "always_logic" in user_config: config["always_logic"] = list(set(config["always_logic"] + user_config["always_logic"]))
        except Exception as e:
            logger.error(f"Config Error: {e}")
    return config

def get_ignore_spec(workspace_root: str):
    """Loads all ignore files into pathspec."""
    patterns = [".git/", "build/", "dist/", "node_modules/", ".dart_tool/", "__pycache__/", "*.db", "*.md", "*.json", "evolutionary-memory/"]
    ignore_files = [".gitignore", ".geminiignore", ".librarianignore"]
    for filename in ignore_files:
        path = Path(workspace_root) / filename
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f: patterns.extend(f.readlines())
            except Exception: pass
    return pathspec.PathSpec.from_lines('gitwildmatch', patterns)

def is_logic_file(content: str, extension: str, config: Dict[str, Any]) -> bool:
    if extension in config.get("always_logic", []): return True
    markers = config.get("ext_markers", {}).get(extension, [])
    for pattern in markers:
        if re.search(pattern, content, re.MULTILINE): return True
    return False

def get_current_sha(workspace_root: str) -> str:
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=workspace_root)
        return res.stdout.strip() if res.returncode == 0 else "PROTO"
    except Exception: return "PROTO"

def get_delta_files(workspace_root: str, ignore_spec) -> Set[Path]:
    delta_files = set()
    if (Path(workspace_root) / ".git").exists():
        try:
            res = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=workspace_root)
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    path_str = line[3:].strip()
                    if " -> " in path_str: path_str = path_str.split(" -> ")[-1]
                    if not ignore_spec.match_file(path_str):
                        delta_files.add(Path(workspace_root) / path_str)
            res = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], capture_output=True, text=True, cwd=workspace_root)
            if res.returncode == 0:
                for line in res.stdout.splitlines(): 
                    path_str = line.strip()
                    if not ignore_spec.match_file(path_str):
                        delta_files.add(Path(workspace_root) / path_str)
            if delta_files: return delta_files
        except Exception: pass
    for root, dirs, files in os.walk(workspace_root):
        rel_root = os.path.relpath(root, workspace_root)
        if rel_root != "." and (any(p in Path(rel_root).parts for p in PRUNE_DIRS) or ignore_spec.match_file(rel_root + "/")):
            dirs[:] = []; continue
        dirs[:] = [d for d in dirs if d not in PRUNE_DIRS and not ignore_spec.match_file(os.path.join(rel_root, d) + "/")]
        for file in files:
            file_path = Path(root) / file
            if file_path.suffix in SUPPORTED_EXTENSIONS and not ignore_spec.match_file(os.path.relpath(file_path, workspace_root)): delta_files.add(file_path)
    return delta_files
