import re
from typing import List, Dict

# Robust Test ID Regex
RAW_TEST_ID_PATTERN = re.compile(r"TEST-\d{8}-\d{6}-\d{4}", re.IGNORECASE)

def parse_tags_multi_line(content: str) -> Dict[str, List[Dict[str, str]]]:
    """
    Parses @trace and @decision tags, supporting YAML-style multi-line blocks.
    Ensures long architectural rationales are captured in full.
    """
    traces, decisions = [], []
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Case-insensitive detection of tag start
        lower_line = line.lower()
        if "@trace" in lower_line or "@decision" in lower_line:
            is_trace = "@trace" in lower_line
            marker = "#" if line.startswith("#") else "//" if line.startswith("//") else "--" if line.startswith("--") else ""
            
            # Extract ID
            id_match = re.search(r"@(trace|decision)\s+(?P<id>FEAT-[\d-]+)", line, re.I)
            if not id_match:
                i += 1; continue
            feat_id = id_match.group("id")
            
            # Collect block lines
            block_lines, j = [], i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                if not next_line.startswith(marker) or "@trace" in next_line.lower() or "@decision" in next_line.lower(): 
                    break
                # Strip marker and leading space
                block_lines.append(next_line[len(marker):].strip())
                j += 1
                
            data = {
                "feat_id": feat_id, 
                "desc": "No description.", 
                "test_id": "UNKNOWN", 
                "decision": "", 
                "rationale": "", 
                "trade_offs": ""
            }
            
            # Handle legacy single-line pipe format if present in the first line
            if "|" in line:
                parts = [p.strip() for p in line.split("|")]
                if is_trace and len(parts) >= 2:
                    data["desc"] = parts[1]
                    if len(parts) >= 3:
                        t_match = re.search(r"TestID:\s*(.*)", parts[2], re.I)
                        data["test_id"] = t_match.group(1).strip() if t_match else parts[2].strip()
                elif not is_trace and len(parts) >= 2:
                    data["decision"] = parts[1]
                    if len(parts) >= 3:
                        r_match = re.search(r"Rationale:\s*(.*)", parts[2], re.I)
                        data["rationale"] = r_match.group(1).strip() if r_match else parts[2].strip()
                    if len(parts) >= 4:
                        tr_match = re.search(r"Trade-?offs:\s*(.*)", parts[3], re.I)
                        data["trade_offs"] = tr_match.group(1).strip() if tr_match else parts[3].strip()

            # --- SMART MULTI-LINE FIELD EXTRACTION ---
            # Map of internal keys to possible YAML-like keys in comments
            key_map = {
                "desc": ["description:", "desc:"],
                "test_id": ["testid:", "test id:", "test_id:"],
                "decision": ["decision:", "choice:"],
                "rationale": ["rationale:", "reason:"],
                "trade_offs": ["trade-offs:", "tradeoffs:"]
            }
            
            current_key = None
            for b_line in block_lines:
                found_new_key = False
                lower_b_line = b_line.lower()
                
                for internal_key, markers in key_map.items():
                    for m in markers:
                        if lower_b_line.startswith(m):
                            current_key = internal_key
                            # Initialize or clear if we find a new key
                            data[current_key] = b_line[len(m):].strip()
                            found_new_key = True
                            break
                    if found_new_key: break
                
                if not found_new_key and current_key:
                    # Append to current multi-line value
                    data[current_key] = (data[current_key] + "\n" + b_line).strip()

            if is_trace: traces.append(data)
            else: decisions.append(data)
            i = j - 1
        i += 1
    return {"traces": traces, "decisions": decisions}
