[CmdletBinding()]
param(
    [string]$ConfigPath = ".\config\devenv.bootstrap.yaml",
    [string]$Platform = "windows-wsl"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$devenvRoot = (Resolve-Path $PSScriptRoot).Path
$pythonLauncher = Join-Path $devenvRoot "run.py"
if (-not (Test-Path $pythonLauncher)) {
    throw "Python launcher not found: $pythonLauncher"
}

$python = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $python) {
    throw "Python is required. Install Python and ensure 'python' is on PATH."
}

& $python.Source $pythonLauncher --config-path $ConfigPath --platform $Platform
if ($LASTEXITCODE -ne 0) {
    throw "Bootstrap launcher failed with exit code $LASTEXITCODE"
}
