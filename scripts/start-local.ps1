param(
    [switch]$Reinstall
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$runDir = Join-Path $root ".local-run"
$logDir = Join-Path $root "logs"
$apiDir = Join-Path $root "services\api"
$webDir = Join-Path $root "apps\web"
$mlFaceDir = Join-Path $root "services\ml-face"
$mlRiskDir = Join-Path $root "services\ml-risk"
$venvPython = Join-Path $apiDir ".venv\Scripts\python.exe"
$nodeModulesDir = Join-Path $webDir "node_modules"

New-Item -ItemType Directory -Force $runDir, $logDir | Out-Null

if (Test-Path (Join-Path $PSScriptRoot "stop-local.ps1")) {
    & (Join-Path $PSScriptRoot "stop-local.ps1") | Out-Null
}

if (!(Test-Path $venvPython)) {
    Write-Host "Creating backend virtual environment..."
    python -m venv (Join-Path $apiDir ".venv")
}

if ($Reinstall -or !(Test-Path (Join-Path $apiDir ".venv\Scripts\uvicorn.exe"))) {
    Write-Host "Installing backend dependencies..."
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -e "$apiDir[dev]"
}

if ($Reinstall -or !(Test-Path $nodeModulesDir)) {
    Write-Host "Installing frontend dependencies..."
    Push-Location $webDir
    npm install
    Pop-Location
}

function Start-GuardianProcess {
    param(
        [string]$Name,
        [string]$WorkingDirectory,
        [string]$FilePath,
        [string[]]$Arguments
    )

    $stdout = Join-Path $logDir "$Name.out.log"
    $stderr = Join-Path $logDir "$Name.err.log"

    $process = Start-Process `
        -FilePath $FilePath `
        -ArgumentList $Arguments `
        -WorkingDirectory $WorkingDirectory `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr `
        -PassThru

    Set-Content -Path (Join-Path $runDir "$Name.pid") -Value $process.Id
    Write-Host "$Name started with PID $($process.Id)"
}

function Wait-ForUrl {
    param(
        [string]$Url,
        [string]$Name,
        [int]$TimeoutSeconds = 45
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $null = & curl.exe --silent --fail --max-time 3 $Url
            if ($LASTEXITCODE -eq 0) {
                Write-Host "$Name is ready at $Url"
                return
            }
        } catch {
            Start-Sleep -Milliseconds 750
        }
        Start-Sleep -Milliseconds 750
    }

    throw "$Name did not become ready within $TimeoutSeconds seconds. Check logs in $logDir."
}

Start-GuardianProcess -Name "ml-face" -WorkingDirectory $mlFaceDir -FilePath $venvPython -Arguments @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8001")
Start-GuardianProcess -Name "ml-risk" -WorkingDirectory $mlRiskDir -FilePath $venvPython -Arguments @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8002")
Start-GuardianProcess -Name "backend" -WorkingDirectory $apiDir -FilePath $venvPython -Arguments @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000")
Start-GuardianProcess -Name "frontend" -WorkingDirectory $webDir -FilePath "npm.cmd" -Arguments @("run", "dev", "--", "--host=127.0.0.1", "--port=5173")

Wait-ForUrl -Name "ML face service" -Url "http://127.0.0.1:8001/health"
Wait-ForUrl -Name "ML risk service" -Url "http://127.0.0.1:8002/health"
Wait-ForUrl -Name "Backend" -Url "http://127.0.0.1:8000/api/v1/health"
Wait-ForUrl -Name "Frontend" -Url "http://127.0.0.1:5173/"

Write-Host ""
Write-Host "Local stack is ready."
Write-Host "Frontend: http://127.0.0.1:5173"
Write-Host "Backend:  http://127.0.0.1:8000/api/v1/health"
Write-Host "Logs:     $logDir"
