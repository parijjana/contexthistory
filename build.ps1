# build.ps1
Write-Host "Building Autonomous Quality Skill container with Podman..." -ForegroundColor Cyan
podman build -t autonomous-quality-skill .

$currentPath = Get-Location
Write-Host "`nRegistration Instruction for Windows (PowerShell):" -ForegroundColor Green
Write-Host "Add this to your ~/.gemini/settings.json:" -ForegroundColor Gray
Write-Host @"
{
  "mcpServers": {
    "autonomous-quality": {
      "command": "podman",
      "args": [
        "run", "-i", "--rm",
        "-v", "$($currentPath):/workspace:Z",
        "autonomous-quality-skill"
      ]
    }
  }
}
"@
