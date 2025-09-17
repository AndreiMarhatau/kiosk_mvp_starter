#requires -version 5.1
param(
    [string]$Name = 'Kiosk',
    [string]$Main = 'main.py',
    [switch]$Clean,
    [string]$LogPath
)

$ErrorActionPreference = 'Stop'

function Write-Step($msg){ Write-Host "[build] $msg" -ForegroundColor Cyan }
function Fail($msg){ Write-Host "[build] $msg" -ForegroundColor Red; exit 1 }

# Go to script directory (kiosk_app)
Set-Location -Path (Split-Path -Parent $MyInvocation.MyCommand.Path)

# 0) Optional transcript logging
$transcribed = $false
if ($LogPath) {
    try {
        $logDir = Split-Path -Parent $LogPath
        if ($logDir -and -not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
        Start-Transcript -Path $LogPath -Append | Out-Null
        $transcribed = $true
        Write-Step "Logging to $LogPath"
    } catch { Write-Host "[build] Failed to start transcript: $($_.Exception.Message)" -ForegroundColor Yellow }
}

# 1) Check venv
$venv = Join-Path (Get-Location) '.venv'
$venvScripts = Join-Path $venv 'Scripts'
$python = Join-Path $venvScripts 'python.exe'
$pysideDeploy = Join-Path $venvScripts 'pyside6-deploy.exe'

if (-not (Test-Path $python)) { Fail "Virtualenv not found: $python. Create it and install PySide6 first." }

# 2) Optional clean
if ($Clean) {
    Write-Step "Cleaning previous build artifacts"
    @('build','dist',$Name) | ForEach-Object {
        if (Test-Path $_) { Remove-Item -Recurse -Force $_ }
    }
}

# 3) Quick syntax check
Write-Step "Syntax check $Main"
& $python -m py_compile $Main

# 4) Ensure pyside6-deploy exists
if (-not (Test-Path $pysideDeploy)) {
    # try module runner
    Write-Step "pyside6-deploy not found as exe. Will invoke as module"
    $pysideDeploy = "$python -m PySide6.scripts.pyside_tool-deploy"
}

# 5) Run deploy (PySide6 6.7+ CLI: pyside6-deploy [options] main_file)
Write-Step "Running pyside6-deploy"
$deployArgs = @(
    '--name', $Name,
    '-f',            # force rebuild if config exists
    $Main            # positional main file
)

if (Test-Path $pysideDeploy) {
    Write-Step "Deploy command: $pysideDeploy $($deployArgs -join ' ')"
    & $pysideDeploy @deployArgs
} else {
    # As module fallback
    Write-Step "Deploy module: PySide6.scripts.pyside_tool-deploy $($deployArgs -join ' ')"
    & $python -m PySide6.scripts.pyside_tool-deploy @deployArgs
}

# 6) Locate result
Write-Step "Build finished. Searching for output..."
$distCandidates = @(
    (Join-Path (Get-Location) "${Name}\dist\${Name}.exe"),
    (Join-Path (Get-Location) "dist\${Name}\${Name}.exe"),
    (Join-Path (Get-Location) "dist\${Name}.exe")
)
$found = $false
foreach($c in $distCandidates){ if(Test-Path $c){ Write-Host "EXE: $c" -ForegroundColor Green; $found=$true } }
if(-not $found){ Write-Host "EXE not found in defaults. Check deploy output for the exact path." -ForegroundColor Yellow }

Write-Step "Done"

if ($transcribed) {
    try { Stop-Transcript | Out-Null } catch {}
}
