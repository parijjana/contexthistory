import pytest
import sys
from pathlib import Path

# Add src to path to import librarian
sys.path.append(str(Path(__file__).parent.parent / "src"))

from librarian.parser import parse_tags_multi_line

def test_python_single_line_trace():
    content = """
# @trace FEAT-20260514-1000 | Implement login | TestID: TEST-20260514-1000-0001
def login():
    pass
"""
    result = parse_tags_multi_line(content)
    assert len(result['traces']) == 1
    assert result['traces'][0]['feat_id'] == "FEAT-20260514-1000"
    assert result['traces'][0]['desc'] == "Implement login"
    assert result['traces'][0]['test_id'] == "TEST-20260514-1000-0001"

def test_python_multi_line_trace():
    content = """
# @trace FEAT-20260514-2000
# Description:
#   This is a multi-line description
#   that spans two lines.
# TestID: TEST-20260514-2000-0001
def complex_logic():
    pass
"""
    result = parse_tags_multi_line(content)
    assert len(result['traces']) == 1
    trace = result['traces'][0]
    assert trace['feat_id'] == "FEAT-20260514-2000"
    assert "This is a multi-line description" in trace['desc']
    assert "that spans two lines." in trace['desc']
    assert trace['test_id'] == "TEST-20260514-2000-0001"

def test_python_multi_line_decision():
    content = """
# @decision FEAT-20260514-3000
# Choice: Argon2 Hashing
# Rationale:
#   Resistant to GPU-based brute-force attacks.
#   It is the current industry standard.
# Trade-offs:
#   High memory overhead.
#   High CPU usage.
"""
    result = parse_tags_multi_line(content)
    assert len(result['decisions']) == 1
    dec = result['decisions'][0]
    assert dec['feat_id'] == "FEAT-20260514-3000"
    assert dec['decision'] == "Argon2 Hashing"
    assert "Resistant to GPU-based brute-force attacks." in dec['rationale']
    assert "High memory overhead." in dec['trade_offs']

def test_dart_multi_line_decision():
    content = """
// @decision FEAT-20260514-4000
// Decision: Riverpod for State Management
// Rationale:
//   Compile-time safety and easy testing.
//   Recommended by the community.
// Trade-offs: Boilerplate for simple cases.
void main() {}
"""
    result = parse_tags_multi_line(content)
    assert len(result['decisions']) == 1
    dec = result['decisions'][0]
    assert dec['feat_id'] == "FEAT-20260514-4000"
    assert dec['decision'] == "Riverpod for State Management"
    assert "Compile-time safety" in dec['rationale']
    assert dec['trade_offs'] == "Boilerplate for simple cases."

def test_sql_multi_line_trace():
    content = """
-- @trace FEAT-20260514-5000
-- Description: 
--   Schema migration for users table.
--   Adding profile_url column.
-- TestID: TEST-20260514-5000-0001
CREATE TABLE users (...);
"""
    result = parse_tags_multi_line(content)
    assert len(result['traces']) == 1
    trace = result['traces'][0]
    assert trace['feat_id'] == "FEAT-20260514-5000"
    assert "Schema migration" in trace['desc']
    assert trace['test_id'] == "TEST-20260514-5000-0001"

def test_mixed_markers_and_indentation():
    # Test if it handles weird spacing and mixed case
    content = """
    // @TRACE FEAT-20260514-6000
    // desc: Indented description
    // TESTID:   TEST-20260514-6000-0001
    
# @DECISION FEAT-20260514-7000
# choice: Mixed markers
# rationale: 
# \tThis line starts with a tab
#     This line starts with spaces
"""
    result = parse_tags_multi_line(content)
    assert len(result['traces']) == 1
    assert result['traces'][0]['desc'] == "Indented description"
    assert result['traces'][0]['test_id'] == "TEST-20260514-6000-0001"
    
    assert len(result['decisions']) == 1
    assert "This line starts with a tab" in result['decisions'][0]['rationale']

def test_multiple_tags_in_file():
    content = """
// @trace FEAT-1 | Trace 1 | TestID: T1
void f1() {}

// @trace FEAT-2 | Trace 2 | TestID: T2
void f2() {}

// @decision FEAT-3 | Dec 1 | Rationale: R1
"""
    result = parse_tags_multi_line(content)
    assert len(result['traces']) == 2
    assert len(result['decisions']) == 1
    assert result['traces'][0]['feat_id'] == "FEAT-1"
    assert result['traces'][1]['feat_id'] == "FEAT-2"
    assert result['decisions'][0]['feat_id'] == "FEAT-3"

def test_malformed_tags_ignored():
    content = """
# @trace FEAT-BAD-FORMAT
# @trace FEAT-123 | Missing test id
# @decision FEAT-456 | Missing rationale
"""
    result = parse_tags_multi_line(content)
    # The current regex is FEAT-[\d-]+, so FEAT-BAD-FORMAT might match if not careful
    # Let's check current behavior. 
    # Actually, ID_MATCH re.search(r"@(trace|decision)\s+(?P<id>FEAT-[\d-]+)", line, re.I)
    # FEAT-BAD-FORMAT will match FEAT-
    # Wait, \d is digit. FEAT-BAD-FORMAT won't match.
    assert len(result['traces']) == 1 # FEAT-123 matches
    assert result['traces'][0]['feat_id'] == "FEAT-123"
    assert len(result['decisions']) == 1 # FEAT-456 matches
    assert result['decisions'][0]['feat_id'] == "FEAT-456"

def test_legacy_pipe_format_compatibility():
    content = """
// @trace FEAT-20260514-8000 | Legacy pipe format | TestID: TEST-PIPE-01
// @decision FEAT-20260514-9000 | Legacy decision | Rationale: Simple | Trade-offs: None
"""
    result = parse_tags_multi_line(content)
    assert len(result['traces']) == 1
    assert result['traces'][0]['desc'] == "Legacy pipe format"
    assert result['traces'][0]['test_id'] == "TEST-PIPE-01"
    
    assert len(result['decisions']) == 1
    assert result['decisions'][0]['decision'] == "Legacy decision"
    assert result['decisions'][0]['rationale'] == "Simple"
    assert result['decisions'][0]['trade_offs'] == "None"

def test_yaml_multiline_block_with_dotall():
    content = """
# @decision FEAT-20260516-1000
# Rationale: |
#   First line of rationale.
#   Second line of rationale.
#   Third line.
# Trade-offs: None.
"""
    result = parse_tags_multi_line(content)
    assert len(result['decisions']) == 1
    rat = result['decisions'][0]['rationale']
    # The current parser doesn't explicitly handle the YAML | pipe, but it uses re.S (DOTALL)
    # in the field extraction. Let's see if it captures the full block.
    assert "First line of rationale." in rat
    assert "Third line." in rat
