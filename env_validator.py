import re

// @trace FEAT-101 | Basic regex for key=value validation | TestID: ENV-01
def validate_env_line(line: str) -> bool:
    \"\"\"Validates if a line follows the KEY=VALUE format.\"\"\"
    pattern = re.compile(r"^[A-Z_]+=[^=]+$")
    return bool(pattern.match(line.strip()))

if __name__ == "__main__":
    test_line = "API_KEY=12345"
    print(f"Is '{test_line}' valid? {validate_env_line(test_line)}")
