import re
import json
from typing import Dict, Any, List

class SemanticDistiller:
    """
    Resilient, multi-language semantic parser for High-Density Context (HDC).
    Uses robust regex patterns to extract logical DNA even from broken code.
    """
    
    @staticmethod
    def distill(content: str, suffix: str) -> str:
        if suffix == ".dart":
            return json.dumps(SemanticDistiller._distill_dart(content), indent=2)
        elif suffix == ".py":
            return json.dumps(SemanticDistiller._distill_python(content), indent=2)
        return json.dumps({"type": "unknown", "raw_len": len(content)})

    @staticmethod
    def _distill_dart(content: str) -> Dict[str, Any]:
        blueprint = {
            "type": "dart_blueprint",
            "classes": [],
            "dependencies": set(),
            "ui_skeleton": []
        }
        
        # 1. Extract Dependencies (Providers, Watches, Imports)
        watch_matches = re.findall(r"context\.watch<(\w+)>", content)
        read_matches = re.findall(r"context\.read<(\w+)>", content)
        ref_matches = re.findall(r"ref\.watch\((\w+)\)", content)
        blueprint["dependencies"].update(watch_matches + read_matches + ref_matches)
        
        # 2. Extract Classes and Methods
        class_blocks = re.finditer(r"class\s+(\w+)(?:\s+extends\s+\w+)?\s*\{", content)
        for cb in class_blocks:
            c_name = cb.group(1)
            # Find methods within a loose range (resilient to broken brackets)
            start = cb.end()
            end = content.find("}", start + 500) # Look ahead 500 chars for a closure
            if end == -1: end = len(content)
            
            methods = re.findall(r"(\w+)\s+(\w+)\s*\([^)]*\)\s*(?:async\s*)?\{", content[start:end])
            blueprint["classes"].append({
                "name": c_name,
                "methods": [{"returns": m[0], "name": m[1]} for m in methods if m[1] not in ('if', 'for', 'while', 'switch')]
            })

        # 3. UI Hierarchy (Heuristic)
        # Extract common widgets in build methods to reconstruct visual intent
        ui_elements = re.findall(r"(Scaffold|AppBar|Column|Row|ListView|Stack|Container|SizedBox|Text|Icon|ClockWidget|PomodoroTimer)\(", content)
        blueprint["ui_skeleton"] = ui_elements[:15] # Keep it high-density
        
        blueprint["dependencies"] = list(blueprint["dependencies"])
        return blueprint

    @staticmethod
    def _distill_python(content: str) -> Dict[str, Any]:
        blueprint = {
            "type": "python_blueprint",
            "classes": [],
            "decorators": set(),
            "imports": []
        }
        
        # 1. Imports
        blueprint["imports"] = re.findall(r"^(?:from\s+(\S+)\s+import|import\s+(\S+))", content, re.MULTILINE)
        blueprint["imports"] = [i[0] or i[1] for i in blueprint["imports"]]
        
        # 2. Decorators (e.g. @mcp.tool, @app.get)
        blueprint["decorators"].update(re.findall(r"@([\w\.]+)", content))
        
        # 3. Classes and Methods
        class_matches = re.finditer(r"^class\s+(\w+)(?:\([^)]*\))?:", content, re.MULTILINE)
        for cm in class_matches:
            c_name = cm.group(1)
            start = cm.end()
            # Find indented methods
            method_matches = re.findall(r"^\s+def\s+(\w+)\s*\(", content[start:start+2000], re.MULTILINE)
            blueprint["classes"].append({
                "name": c_name,
                "methods": method_matches
            })
            
        blueprint["decorators"] = list(blueprint["decorators"])
        return blueprint
