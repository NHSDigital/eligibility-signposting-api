[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Read-ChoiceValue {
    param(
        [string]$Prompt,
        [string]$Default,
        [string[]]$Allowed
    )
    while ($true) {
        $value = Read-Host "$Prompt [$Default]"
        if ([string]::IsNullOrWhiteSpace($value)) { $value = $Default }
        if ($Allowed -contains $value) { return $value }
        Write-Host "Allowed values: $($Allowed -join ', ')" -ForegroundColor Yellow
    }
}

function Read-YesNo {
    param(
        [string]$Prompt,
        [bool]$Default = $false
    )
    $hint = if ($Default) { "Y/n" } else { "y/N" }
    $value = Read-Host "$Prompt [$hint]"
    if ([string]::IsNullOrWhiteSpace($value)) { return $Default }
    return @("y", "yes") -contains $value.Trim().ToLowerInvariant()
}

function Read-OptionalValue {
    param([string]$Prompt, [string]$Default)
    $value = Read-Host "$Prompt [$Default]"
    if ([string]::IsNullOrWhiteSpace($value)) { return $Default }
    return $value.Trim()
}

function ConvertTo-BashSingleQuoted {
    param([string]$Value)
    return "'" + $Value.Replace("'", "'""'""'") + "'"
}

function ConvertTo-PlainText {
    param([Security.SecureString]$SecureString)
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureString)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
}

function Read-SecretValue {
    param([string]$Prompt)
    $secret = Read-Host $Prompt -AsSecureString
    $value = ConvertTo-PlainText -SecureString $secret
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "Password cannot be empty."
    }
    return $value
}

function Test-WSLUserLogin {
    param(
        [string]$Distro,
        [string]$User
    )

    $null = & wsl.exe -d $Distro -u $User -- bash -lc "id -u >/dev/null"
    return ($LASTEXITCODE -eq 0)
}

function Read-ValidatedSudoPassword {
    param(
        [string]$Distro,
        [string]$User,
        [int]$MaxAttempts = 3
    )

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        $candidate = Read-SecretValue -Prompt "Enter sudo password for WSL user '$User'"
        $candidateB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($candidate))

        $validateScript = "set -euo pipefail; printf '%s' '$candidateB64' | base64 -d | sudo -S -p '' -k true >/dev/null"
        $null = & wsl.exe -d $Distro -u $User -- bash -lc $validateScript
        if ($LASTEXITCODE -eq 0) {
            return $candidate
        }

        if ($attempt -lt $MaxAttempts) {
            Write-Host "Invalid sudo password. Please try again." -ForegroundColor Yellow
        }
    }

    throw "Failed to validate sudo credentials after $MaxAttempts attempts."
}

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Invoke-WSLScript {
    param(
        [Parameter(Mandatory = $true)][string]$Distro,
        [Parameter(Mandatory = $false)][string]$User,
        [Parameter(Mandatory = $true)][string]$ScriptText
    )

    $encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($ScriptText))
    $wslArgs = @("-d", $Distro)
    if (-not [string]::IsNullOrWhiteSpace($User)) { $wslArgs += @("-u", $User) }
    $wslArgs += @("--", "bash", "-lc", "printf '%s' '$encoded' | base64 -d | bash")

    $output = & wsl.exe @wslArgs
    if ($LASTEXITCODE -ne 0) { throw "WSL command failed." }
    return $output
}

function Get-GitOriginUrl {
    param([string]$RemoteName)

    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "git is not installed or not on PATH."
    }

    $repoPath = if (-not [string]::IsNullOrWhiteSpace($env:DEVENV_REPO_ROOT) -and (Test-Path $env:DEVENV_REPO_ROOT)) {
        $env:DEVENV_REPO_ROOT
    }
    else {
        (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
    }

    $origin = (& git -C $repoPath remote get-url $RemoteName 2>$null | Select-Object -First 1)
    if ([string]::IsNullOrWhiteSpace($origin)) {
        throw "Missing git remote '$RemoteName' at $repoPath"
    }

    return $origin.Trim()
}

function Ensure-WSLAndDistro {
    param(
        [string]$Distro,
        [string]$Mode,
        [string]$RerunCommand
    )

    if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
        if ($Mode -eq "check") { throw "WSL is not available." }
        if (-not (Read-YesNo -Prompt "WSL is missing. Install now?" -Default $true)) { throw "Cancelled." }
        if (-not (Test-IsAdministrator)) { throw "Run PowerShell as Administrator to install WSL." }

        & wsl.exe --install -d $Distro
        if ($LASTEXITCODE -ne 0) { throw "WSL install failed." }
        Write-Host "WSL install started. Reboot if prompted, then rerun: $RerunCommand" -ForegroundColor Yellow
        exit 0
    }

    & wsl.exe --status *> $null
    if ($LASTEXITCODE -ne 0) {
        if ($Mode -eq "check") { throw "WSL is not available." }
        if (-not (Read-YesNo -Prompt "WSL not configured. Install now?" -Default $true)) { throw "Cancelled." }
        if (-not (Test-IsAdministrator)) { throw "Run PowerShell as Administrator to install WSL." }

        & wsl.exe --install -d $Distro
        if ($LASTEXITCODE -ne 0) { throw "WSL install failed." }
        Write-Host "WSL install started. Reboot if prompted, then rerun: $RerunCommand" -ForegroundColor Yellow
        exit 0
    }

    $distros = & wsl.exe -l -q 2>$null
    if ($LASTEXITCODE -ne 0) { throw "Unable to list WSL distros." }

    $installed = @($distros | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    if ($installed -notcontains $Distro) {
        if ($Mode -eq "check") { throw "Required distro not installed: $Distro" }
        if (-not (Read-YesNo -Prompt "Distro '$Distro' is missing. Install now?" -Default $true)) { throw "Cancelled." }
        if (-not (Test-IsAdministrator)) { throw "Run PowerShell as Administrator to install '$Distro'." }

        & wsl.exe --install -d $Distro
        if ($LASTEXITCODE -ne 0) { throw "Distro install failed." }
        Write-Host "Distro install started. Complete first-run setup, then rerun: $RerunCommand" -ForegroundColor Yellow
        exit 0
    }
}

function Get-WSLWhoAmI {
    param([string]$Distro)
    $who = (& wsl.exe -d $Distro -- bash -lc "whoami" 2>$null | Select-Object -First 1)
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($who)) { return "" }
    return $who.Trim()
}

function Convert-WindowsPathToWslPath {
    param(
        [string]$Distro,
        [string]$WindowsPath
    )

    $normalizedPath = $WindowsPath -replace "\\", "/"
    $mapped = (& wsl.exe -d $Distro -- wslpath -a "$normalizedPath" 2>$null | Select-Object -First 1)
    if ([string]::IsNullOrWhiteSpace($mapped)) {
        throw "Failed to map Windows path to WSL path: $WindowsPath"
    }
    return $mapped.Trim()
}

# Paths + config
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$DevenvRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$ConfigPath = if ($env:DEVENV_CONFIG_PATH) { $env:DEVENV_CONFIG_PATH } else { Join-Path $DevenvRoot "config\devenv.bootstrap.yaml" }

if (-not (Test-Path $ConfigPath)) {
    throw "Config file not found: $ConfigPath"
}

if ([string]::IsNullOrWhiteSpace($env:DEVENV_CONFIG_JSON)) {
    throw "DEVENV_CONFIG_JSON is missing. Run bootstrap via devenv/run.py so YAML is parsed by Python first."
}

$config = $env:DEVENV_CONFIG_JSON | ConvertFrom-Json
$platformKey = if ($env:DEVENV_PLATFORM) { $env:DEVENV_PLATFORM } else { "windows-wsl" }
$platform = $config.platforms.$platformKey
if ($null -eq $platform -or -not $platform.enabled) {
    throw "Platform '$platformKey' is not enabled in config."
}

$mode = Read-ChoiceValue -Prompt "Select mode: check or create" -Default "check" -Allowed @("check", "create")

$remoteName = [string]$config.git.remote_name
$actualOriginUrl = Get-GitOriginUrl -RemoteName $remoteName
$expectedOriginUrl = [string]$config.git.clone_url

if (-not [string]::IsNullOrWhiteSpace($expectedOriginUrl) -and $actualOriginUrl -ne $expectedOriginUrl) {
    throw "Origin URL mismatch. YAML clone_url='$expectedOriginUrl', current='$actualOriginUrl'."
}

$distro = [string]$platform.wsl.distro
$wslRepoRoot = [string]$platform.wsl.repo_root
$wslRepoName = [string]$platform.wsl.repo_name
$wslBootstrapRel = [string]$platform.wsl.bootstrap_script
$defaultLinuxUser = [string]$platform.wsl.linux_user.default

$rerunCommand = "python `"$DevenvRoot\run.py`" --platform windows-wsl"
Ensure-WSLAndDistro -Distro $distro -Mode $mode -RerunCommand $rerunCommand

$wslWhoAmI = Get-WSLWhoAmI -Distro $distro
$wslRunUser = Read-OptionalValue -Prompt "WSL username" -Default ($(if ([string]::IsNullOrWhiteSpace($wslWhoAmI)) { $defaultLinuxUser } else { $wslWhoAmI }))
$userCanLogin = Test-WSLUserLogin -Distro $distro -User $wslRunUser
if (-not $userCanLogin) {
    throw "WSL user '$wslRunUser' does not exist or cannot login in distro '$distro'."
}
$wslRepoRootResolved = ([string]$wslRepoRoot).Replace("{user}", $wslRunUser)
$wslPassword = Read-ValidatedSudoPassword -Distro $distro -User $wslRunUser -MaxAttempts 3
$wslPasswordB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($wslPassword))

$gitPatB64 = ""
$gitUsername = "x-access-token"
$cloneUrl = [string]$config.git.clone_url
if ($mode -eq "create" -and $cloneUrl.StartsWith("https://")) {
    $gitUsername = Read-OptionalValue -Prompt "Enter GitHub username for PAT auth" -Default $env:USERNAME
    $gitPat = Read-SecretValue -Prompt "Enter GitHub Personal Access Token (PAT) for HTTPS git operations"
    $gitPatB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($gitPat))
}

$repoRootWsl = Convert-WindowsPathToWslPath -Distro $distro -WindowsPath $RepoRoot
$configWsl = Convert-WindowsPathToWslPath -Distro $distro -WindowsPath $ConfigPath
$bootstrapAbsWsl = "$repoRootWsl/$wslBootstrapRel"

Write-Host ""
Write-Host "Mode:        $mode"
Write-Host "Origin URL:  $actualOriginUrl"
Write-Host "WSL distro:  $distro"
Write-Host "WSL user:    $wslRunUser"
Write-Host "Bootstrap:   $bootstrapAbsWsl"
Write-Host ""

$delegate = @'
set -euo pipefail

export DEVENV_MODE=__MODE__
export DEVENV_CONFIG_PATH=__CONFIG_PATH__
export DEVENV_WINDOWS_ORIGIN_URL=__WINDOWS_ORIGIN_URL__
export DEVENV_WSL_REPO_ROOT=__WSL_REPO_ROOT__
export DEVENV_WSL_REPO_NAME=__WSL_REPO_NAME__
export DEVENV_WSL_CLONE_URL=__WSL_CLONE_URL__
export DEVENV_WSL_BASE_BRANCH=__WSL_BASE_BRANCH__
export DEVENV_INIT_BRANCH_PATTERN=__INIT_BRANCH_PATTERN__
export DEVENV_INIT_BRANCH_TIMESTAMP_FORMAT=__INIT_BRANCH_TIMESTAMP_FORMAT__
export DEVENV_INIT_BRANCH_PUSH_ON_CREATE=__INIT_BRANCH_PUSH__
export DEVENV_INIT_BRANCH_FAIL_IF_EXISTS=__INIT_BRANCH_FAIL__
export DEVENV_WSL_USERNAME=__WSL_USERNAME__
export DEVENV_SUDO_PASSWORD_B64=__SUDO_PASSWORD_B64__
export DEVENV_GIT_USERNAME=__GIT_USERNAME__
export DEVENV_GIT_PAT_B64=__GIT_PAT_B64__

if [ ! -f __BOOTSTRAP_PATH__ ]; then
  echo "WSL bootstrap script not found: __BOOTSTRAP_PATH__" >&2
  exit 1
fi

chmod +x __BOOTSTRAP_PATH__
bash __BOOTSTRAP_PATH__
'@

$delegate = $delegate.
    Replace("__MODE__", (ConvertTo-BashSingleQuoted $mode)).
    Replace("__CONFIG_PATH__", (ConvertTo-BashSingleQuoted $configWsl)).
    Replace("__WINDOWS_ORIGIN_URL__", (ConvertTo-BashSingleQuoted $actualOriginUrl)).
    Replace("__WSL_REPO_ROOT__", (ConvertTo-BashSingleQuoted $wslRepoRootResolved)).
    Replace("__WSL_REPO_NAME__", (ConvertTo-BashSingleQuoted $wslRepoName)).
    Replace("__WSL_CLONE_URL__", (ConvertTo-BashSingleQuoted ([string]$config.git.clone_url))).
    Replace("__WSL_BASE_BRANCH__", (ConvertTo-BashSingleQuoted ([string]$config.git.default_base_branch))).
    Replace("__INIT_BRANCH_PATTERN__", (ConvertTo-BashSingleQuoted ([string]$config.git.init_branch.pattern))).
    Replace("__INIT_BRANCH_TIMESTAMP_FORMAT__", (ConvertTo-BashSingleQuoted ([string]$config.git.init_branch.timestamp_format))).
    Replace("__INIT_BRANCH_PUSH__", (ConvertTo-BashSingleQuoted (([bool]$config.git.init_branch.push_on_create).ToString().ToLowerInvariant()))).
    Replace("__INIT_BRANCH_FAIL__", (ConvertTo-BashSingleQuoted (([bool]$config.git.init_branch.fail_if_exists_on_remote).ToString().ToLowerInvariant()))).
    Replace("__WSL_USERNAME__", (ConvertTo-BashSingleQuoted $wslRunUser)).
    Replace("__SUDO_PASSWORD_B64__", (ConvertTo-BashSingleQuoted $wslPasswordB64)).
    Replace("__GIT_USERNAME__", (ConvertTo-BashSingleQuoted $gitUsername)).
    Replace("__GIT_PAT_B64__", (ConvertTo-BashSingleQuoted $gitPatB64)).
    Replace("__BOOTSTRAP_PATH__", (ConvertTo-BashSingleQuoted $bootstrapAbsWsl))

Invoke-WSLScript -Distro $distro -User $wslRunUser -ScriptText $delegate | Out-Host
Write-Host "`n$($mode.Substring(0,1).ToUpper() + $mode.Substring(1)) complete." -ForegroundColor Green
