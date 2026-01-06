---
description: Backup Antigravity conversations and artifacts to the project directory based on a whitelist
---

1. Create the destination directory if it doesn't exist
```powershell
if (!(Test-Path -Path "\\wsl.localhost\Ubuntu\home\mattb\projects\dashboard_interface_project\antigravity")) { New-Item -ItemType Directory -Force -Path "\\wsl.localhost\Ubuntu\home\mattb\projects\dashboard_interface_project\antigravity" }
```

2. Backup Listed Conversations
```powershell
$backupList = Get-Content "\\wsl.localhost\Ubuntu\home\mattb\projects\dashboard_interface_project\.agent\backup_list.txt"
$sourceConv = "C:\Users\MattBorgeson\.gemini\antigravity\conversations"
$destConv = "\\wsl.localhost\Ubuntu\home\mattb\projects\dashboard_interface_project\antigravity\conversations"
$sourceBrain = "C:\Users\MattBorgeson\.gemini\antigravity\brain"
$destBrain = "\\wsl.localhost\Ubuntu\home\mattb\projects\dashboard_interface_project\antigravity\brain"

if (!(Test-Path -Path $destConv)) { New-Item -ItemType Directory -Force -Path $destConv }
if (!(Test-Path -Path $destBrain)) { New-Item -ItemType Directory -Force -Path $destBrain }

foreach ($id in $backupList) {
    if (-not [string]::IsNullOrWhiteSpace($id)) {
        # Backup Conversation File (.pb)
        $pbFile = Join-Path $sourceConv "$id.pb"
        if (Test-Path $pbFile) {
            Copy-Item -Path $pbFile -Destination $destConv -Force
            Write-Host "Backed up conversation: $id"
        } else {
            Write-Warning "Conversation file not found: $id"
        }

        # Backup Brain Directory
        $brainDir = Join-Path $sourceBrain $id
        $targetBrainDir = Join-Path $destBrain $id
        if (Test-Path $brainDir) {
            robocopy $brainDir $targetBrainDir /MIR /R:3 /W:1 /NJH /NJS
            if ($LASTEXITCODE -gt 7) { Write-Error "Robocopy failed for brain dir $id with code $LASTEXITCODE" }
            Write-Host "Backed up brain artifacts: $id"
        }
    }
}
```
