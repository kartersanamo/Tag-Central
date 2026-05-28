# Build Tag Center for Windows (Tag Center.exe in dist\).
# Run in PowerShell from the project root:
#   .\build-windows.ps1

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
Set-Location $Root

Write-Host "==> Tag Center — Windows build"
Write-Host "    Project: $Root"

$Python = if ($env:PYTHON) { $env:PYTHON } else { "python" }

if (-not (Test-Path ".venv")) {
    Write-Host "==> Creating virtual environment"
    & $Python -m venv .venv
}

$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$VenvPip = Join-Path $Root ".venv\Scripts\pip.exe"

Write-Host "==> Installing build dependencies"
& $VenvPip install -q --upgrade pip
& $VenvPip install -q -r requirements-build.txt

Write-Host "==> Generating icons (.png, .ico)"
& $VenvPython scripts/generate_icons.py

if (-not (Test-Path "assets\icon.ico")) {
    throw "assets\icon.ico was not created."
}

Write-Host "==> Running PyInstaller"
& (Join-Path $Root ".venv\Scripts\pyinstaller.exe") --noconfirm --clean scripts\tag_central.spec

$ExePath = Join-Path $Root "dist\Tag Center.exe"
if (-not (Test-Path $ExePath)) {
    throw "Expected $ExePath"
}

Write-Host ""
Write-Host "Build complete:"
Write-Host "  $ExePath"
Write-Host ""
Write-Host "User data when running the .exe:"
Write-Host "  %APPDATA%\TagCenter\"
