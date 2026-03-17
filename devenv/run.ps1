[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "platforms\windows\bootstrap.ps1"
& powershell.exe -ExecutionPolicy Bypass -File $scriptPath
exit $LASTEXITCODE