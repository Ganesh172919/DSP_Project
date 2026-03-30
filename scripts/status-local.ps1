$ErrorActionPreference = "SilentlyContinue"

$root = Split-Path -Parent $PSScriptRoot
$runDir = Join-Path $root ".local-run"

if (!(Test-Path $runDir)) {
    Write-Host "No local services have been started yet."
    exit 0
}

Get-ChildItem -Path $runDir -Filter "*.pid" | ForEach-Object {
    $processId = [int](Get-Content $_.FullName)
    $process = Get-Process -Id $processId
    if ($process) {
        Write-Host "$($_.BaseName): running (PID $processId)"
    } else {
        Write-Host "$($_.BaseName): not running (stale pid file)"
    }
}
