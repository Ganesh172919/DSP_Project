$ErrorActionPreference = "SilentlyContinue"

$root = Split-Path -Parent $PSScriptRoot
$runDir = Join-Path $root ".local-run"

if (!(Test-Path $runDir)) {
    Write-Host "No local-run state directory found."
    exit 0
}

Get-ChildItem -Path $runDir -Filter "*.pid" | ForEach-Object {
    $processId = Get-Content $_.FullName
    if ($processId) {
        Stop-Process -Id ([int]$processId) -Force
        Write-Host "Stopped PID $processId from $($_.Name)"
    }
    Remove-Item $_.FullName -Force
}

Write-Host "Local services stopped."
