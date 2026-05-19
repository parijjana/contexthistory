#!/bin/bash
# build.sh
echo "Building Autonomous Quality Skill container with Podman..."
podman build -t autonomous-quality-skill .

CURRENT_PATH=$(pwd)
echo -e "\nRegistration Instruction for Linux/macOS:"
echo "Add this to your ~/.gemini/settings.json:"
cat <<EOF
{
  "mcpServers": {
    "autonomous-quality": {
      "command": "podman",
      "args": [
        "run", "-i", "--rm",
        "-v", "$CURRENT_PATH:/workspace:Z",
        "autonomous-quality-skill"
      ]
    }
  }
}
EOF
