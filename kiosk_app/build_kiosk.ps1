#requires -version 5.1
param(
  [string]$Name = 'Kiosk',
  [switch]$Clean,
  [string]$LogDir = 'build_logs'
)

$ErrorActionPreference = 'Stop'
function Step($m){ Write-Host "[kiosk-build] $m" -ForegroundColor Cyan }
function Fail($m){ Write-Host "[kiosk-build] $m" -ForegroundColor Red; exit 1 }

try{
  Step 'Locate Python launcher'
  $py = (Get-Command py.exe -ErrorAction SilentlyContinue)
  if(-not $py){ $py = (Get-Command python.exe -ErrorAction SilentlyContinue) }
  if(-not $py){ Fail 'Python not found. Install Python 3.x and try again.' }

  Step 'Ensure virtualenv (kiosk_app/.venv)'
  $venvPath = Join-Path (Resolve-Path '.') 'kiosk_app/.venv'
  if(-not (Test-Path $venvPath)){
    & $py.Source -m venv $venvPath
  }

  $python = Join-Path $venvPath 'Scripts/python.exe'
  if(-not (Test-Path $python)){ Fail "Venv python not found: $python" }

  Step 'Upgrade pip'
  & $python -m pip install --upgrade pip wheel setuptools

  Step 'Install dependencies'
  $req = Join-Path (Resolve-Path 'kiosk_app') 'requirements.txt'
  if(Test-Path $req){
    & $python -m pip install -r $req
  } else {
    # Base deps for kiosk_app
    & $python -m pip install "PySide6>=6.5" requests
  }

  Step 'Run deploy (standalone exe)'
  $buildScript = Join-Path (Resolve-Path 'kiosk_app') 'build_exe.ps1'
  if(-not (Test-Path $buildScript)){ Fail "Missing kiosk_app/build_exe.ps1" }
  # prepare log file
  if(-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
  $timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
  $logFile = Join-Path $LogDir ("deploy-" + $timestamp + ".log")
  if($Clean){
    & $buildScript -Name $Name -Main 'main.py' -Clean -LogPath $logFile
  } else {
    & $buildScript -Name $Name -Main 'main.py' -LogPath $logFile
  }
  Step ("Log file: " + (Resolve-Path $logFile))

  Step 'Try open output folder'
  $candidates = @(
    "kiosk_app/$Name/dist",
    "kiosk_app/dist/$Name",
    "kiosk_app/dist"
  )
  foreach($p in $candidates){ if(Test-Path $p){ Start-Process explorer.exe (Resolve-Path $p); break } }

  Step 'Done'
}
catch{
  Fail $_.Exception.Message
}
