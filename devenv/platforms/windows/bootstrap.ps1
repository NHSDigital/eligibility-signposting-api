[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

function Import-SimpleEnv {
    param([string]$Path)

    $map = @{}
    foreach ($rawLine in Get-Content -Path $Path) {
        $line = $rawLine.Trim()
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        if ($line.StartsWith("#")) { continue }

        $idx = $line.IndexOf("=")
        if ($idx -lt 1) { continue }

        $key = $line.Substring(0, $idx).Trim()
        $value = $line.Substring($idx + 1).Trim()
        $map[$key] = $value
    }

    return $map
}

function Get-ToolVersion {
    param(
        [string]$RepoRoot,
        [string]$Tool,
        [string]$Fallback
    )

    $toolVersionsPath = Join-Path $RepoRoot ".tool-versions"
    if (-not (Test-Path $toolVersionsPath)) {
        return $Fallback
    }

    foreach ($line in Get-Content $toolVersionsPath) {
        $trimmed = $line.Trim()
        if ([string]::IsNullOrWhiteSpace($trimmed)) { continue }
        if ($trimmed.StartsWith("#")) { continue }

        $parts = $trimmed -split "\s+"
        if ($parts.Count -ge 2 -and $parts[0] -eq $Tool) {
            return $parts[1]
        }
    }

    return $Fallback
}

function Read-ChoiceValue {
    param(
        [string]$Prompt,
        [string]$Default,
        [string[]]$Allowed
    )

    while ($true) {
        $value = Read-Host "$Prompt [$Default]"
        if ([string]::IsNullOrWhiteSpace($value)) {
            $value = $Default
        }

        if ($Allowed -contains $value) {
            return $value
        }

        Write-Host "Allowed values: $($Allowed -join ', ')" -ForegroundColor Yellow
    }
}

function Read-YesNo {
    param(
        [string]$Prompt,
        [bool]$Default = $false
    )

    $defaultText = if ($Default) { "Y/n" } else { "y/N" }
    $value = Read-Host "$Prompt [$defaultText]"

    if ([string]::IsNullOrWhiteSpace($value)) {
        return $Default
    }

    return @("y", "yes") -contains $value.Trim().ToLowerInvariant()
}

function Read-OptionalValue {
    param(
        [string]$Prompt,
        [string]$Default
    )

    $value = Read-Host "$Prompt [$Default]"
    if ([string]::IsNullOrWhiteSpace($value)) {
        return $Default
    }

    return $value.Trim()
}

function Read-SecretPlainText {
    param([string]$Prompt)

    $secure = Read-Host $Prompt -AsSecureString
    return ConvertTo-PlainText -SecureString $secure
}

function Read-SecretWithConfirmation {
    param([string]$Prompt)

    $first = Read-Host $Prompt -AsSecureString
    $second = Read-Host "Confirm password" -AsSecureString

    $plain1 = ConvertTo-PlainText -SecureString $first
    $plain2 = ConvertTo-PlainText -SecureString $second

    if ($plain1 -ne $plain2) {
        throw "Passwords do not match."
    }

    return $plain1
}

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function ConvertTo-PlainText {
    param([Security.SecureString]$SecureString)

    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureString)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
}

function ConvertTo-BashSingleQuoted {
    param([string]$Value)
    return "'" + $Value.Replace("'", "'""'""'") + "'"
}

function Get-SanitizedLinuxUser {
    param([string]$Candidate)

    $value = $Candidate.ToLowerInvariant() -replace "[^a-z0-9_-]", ""
    if ([string]::IsNullOrWhiteSpace($value)) {
        return "developer"
    }

    return $value
}

function Invoke-WSLScript {
    param(
        [string]$Distro,
        [string]$User,
        [string]$ScriptText
    )

    $encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($ScriptText))
    $args = @("-d", $Distro)

    if (-not [string]::IsNullOrWhiteSpace($User)) {
        $args += @("-u", $User)
    }

    $args += @("--", "bash", "-lc", "printf '%s' '$encoded' | base64 -d | bash")
    $output = & wsl.exe @args
    if ($LASTEXITCODE -ne 0) {
        throw "WSL command failed."
    }

    return $output
}

function Test-WSLAvailable {
    $wsl = Get-Command wsl.exe -ErrorAction SilentlyContinue
    if ($null -eq $wsl) {
        return $false
    }

    & wsl.exe --status *> $null
    return $LASTEXITCODE -eq 0
}

function Get-InstalledDistros {
    $lines = & wsl.exe -l -q 2>$null
    if ($LASTEXITCODE -ne 0) {
        return @()
    }

    return @($lines | ForEach-Object { $_.Trim() } | Where-Object { $_ })
}

function Ensure-WSLAndDistro {
    param(
        [string]$Distro,
        [string]$Mode
    )

    if (-not (Test-WSLAvailable)) {
        if ($Mode -eq "check") {
            throw "WSL is not available."
        }

        if (-not (Test-IsAdministrator)) {
            throw "WSL is not available. Re-run PowerShell as Administrator."
        }

        Write-Host "Installing WSL and $Distro..." -ForegroundColor Cyan
        & wsl.exe --install -d $Distro
        if ($LASTEXITCODE -ne 0) {
            throw "WSL install failed."
        }

        Write-Host "WSL install initiated. Reboot if prompted, then re-run .\devenv\run.ps1" -ForegroundColor Yellow
        exit 0
    }

    $distros = Get-InstalledDistros
    if ($distros -notcontains $Distro) {
        if ($Mode -eq "check") {
            throw "$Distro is not installed."
        }

        if (-not (Test-IsAdministrator)) {
            throw "$Distro is missing. Re-run PowerShell as Administrator."
        }

        Write-Host "Installing distro $Distro..." -ForegroundColor Cyan
        & wsl.exe --install -d $Distro
        if ($LASTEXITCODE -ne 0) {
            throw "Distro install failed."
        }

        Write-Host "Distro install initiated. Re-run .\devenv\run.ps1 after setup completes." -ForegroundColor Yellow
        exit 0
    }
}

function Get-CurrentWSLUser {
    param([string]$Distro)

    try {
        $whoami = (& wsl.exe -d $Distro -- bash -lc "whoami" 2>$null | Select-Object -First 1).Trim()
        if ([string]::IsNullOrWhiteSpace($whoami)) {
            return $null
        }

        return $whoami
    }
    catch {
        return $null
    }
}

function Ensure-WSLUser {
    param(
        [string]$Distro,
        [string]$PreferredUser,
        [string]$Mode
    )

    $currentUser = Get-CurrentWSLUser -Distro $Distro
    if (-not [string]::IsNullOrWhiteSpace($currentUser) -and $currentUser -ne "root") {
        $linuxUser = Read-OptionalValue -Prompt "WSL Linux username" -Default $currentUser
        $checkUserScript = "id -u $(ConvertTo-BashSingleQuoted $linuxUser) >/dev/null 2>&1"
        Invoke-WSLScript -Distro $Distro -User "root" -ScriptText $checkUserScript | Out-Null

        $password = Read-SecretPlainText -Prompt "Enter sudo password for WSL user '$linuxUser'"
        return @{
            User = $linuxUser
            PasswordB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($password))
        }
    }

    if ($Mode -eq "check") {
        throw "No non-root default WSL user is configured."
    }

    $linuxUser = Get-SanitizedLinuxUser -Candidate $PreferredUser
    Write-Host "Creating WSL sudo user: $linuxUser" -ForegroundColor Cyan

    $password = Read-SecretWithConfirmation -Prompt "Enter password for WSL user '$linuxUser'"
    $passwordB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($password))

    $template = @'
set -euo pipefail

LINUX_USER=__LINUX_USER__
PASSWORD_B64=__PASSWORD_B64__

if ! id -u "$LINUX_USER" >/dev/null 2>&1; then
  useradd -m -s /bin/bash "$LINUX_USER"
fi

usermod -aG sudo "$LINUX_USER"

PASSWORD="$(printf '%s' "$PASSWORD_B64" | base64 -d)"
printf '%s:%s\n' "$LINUX_USER" "$PASSWORD" | chpasswd

python3 - <<'PY'
from pathlib import Path

linux_user = "__LINUX_USER_VALUE__"
path = Path("/etc/wsl.conf")
content = path.read_text() if path.exists() else ""
lines = content.splitlines()

out = []
in_user = False
default_written = False

for line in lines:
    stripped = line.strip()
    if stripped == "[user]":
        in_user = True
        out.append(line)
        continue
    if in_user and stripped.startswith("default="):
        out.append(f"default={linux_user}")
        default_written = True
        in_user = False
        continue
    if stripped.startswith("[") and stripped.endswith("]") and in_user and not default_written:
        out.append(f"default={linux_user}")
        default_written = True
        in_user = False
    out.append(line)

if not default_written:
    if out and out[-1].strip():
        out.append("")
    out.append("[user]")
    out.append(f"default={linux_user}")

path.write_text("\n".join(out).rstrip() + "\n")
PY
'@

    $script = $template.
        Replace("__LINUX_USER__", (ConvertTo-BashSingleQuoted $linuxUser)).
        Replace("__PASSWORD_B64__", (ConvertTo-BashSingleQuoted $passwordB64)).
        Replace("__LINUX_USER_VALUE__", $linuxUser)

    Invoke-WSLScript -Distro $Distro -User "root" -ScriptText $script | Out-Null

    & wsl.exe --terminate $Distro *> $null
    Start-Sleep -Seconds 2

    return @{
        User = $linuxUser
        PasswordB64 = $passwordB64
    }
}

function Get-RepoOriginUrl {
    param([string]$RepoRoot)

    $url = (& git -C $RepoRoot remote get-url origin 2>$null | Select-Object -First 1)
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($url)) {
        throw "Unable to read git remote origin from the current repo."
    }

    return $url.Trim()
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$DevenvRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$DefaultsPath = Join-Path $DevenvRoot "config\defaults.env"
$defaults = Import-SimpleEnv -Path $DefaultsPath

$repoOriginUrl = Get-RepoOriginUrl -RepoRoot $RepoRoot
$repoName = [IO.Path]::GetFileNameWithoutExtension($repoOriginUrl.Split("/")[-1])
$defaultLinuxUser = if ([string]::IsNullOrWhiteSpace($defaults["WSL_LINUX_USER"])) {
    Get-SanitizedLinuxUser -Candidate $env:USERNAME
} else {
    Get-SanitizedLinuxUser -Candidate $defaults["WSL_LINUX_USER"]
}

$mode = Read-ChoiceValue -Prompt "Select mode: check or create" -Default "check" -Allowed @("check", "create")

$distro = $defaults["WSL_DISTRO"]
$wslRepoRoot = $defaults["WSL_REPO_ROOT"]
$dockerStrategy = $defaults["DOCKER_STRATEGY"]

$pythonVersion = Get-ToolVersion -RepoRoot $RepoRoot -Tool "python" -Fallback $defaults["PYTHON_VERSION"]
$poetryVersion = Get-ToolVersion -RepoRoot $RepoRoot -Tool "poetry" -Fallback $defaults["POETRY_VERSION"]
$nodeVersion = Get-ToolVersion -RepoRoot $RepoRoot -Tool "nodejs" -Fallback $defaults["NODE_VERSION"]
$terraformVersion = Get-ToolVersion -RepoRoot $RepoRoot -Tool "terraform" -Fallback $defaults["TERRAFORM_VERSION"]
$preCommitVersion = Get-ToolVersion -RepoRoot $RepoRoot -Tool "pre-commit" -Fallback $defaults["PRECOMMIT_VERSION"]
$valeVersion = Get-ToolVersion -RepoRoot $RepoRoot -Tool "vale" -Fallback $defaults["VALE_VERSION"]
$actVersion = Get-ToolVersion -RepoRoot $RepoRoot -Tool "act" -Fallback $defaults["ACT_VERSION"]

$runProjectSetup = $defaults["RUN_PROJECT_SETUP"]
$runValidation = $defaults["RUN_VALIDATION"]
$runUnitTests = $defaults["RUN_UNIT_TESTS"]
$runBuild = $defaults["RUN_BUILD"]
$runIntegrationTests = $defaults["RUN_INTEGRATION_TESTS"]

if (Read-YesNo -Prompt "Override defaults?" -Default $false) {
    $distro = Read-OptionalValue -Prompt "WSL distro" -Default $distro
    $wslRepoRoot = Read-OptionalValue -Prompt "WSL repo root" -Default $wslRepoRoot
    $dockerStrategy = Read-ChoiceValue -Prompt "Docker strategy" -Default $dockerStrategy -Allowed @("engine", "desktop", "skip")

    $pythonVersion = Read-OptionalValue -Prompt "Python version" -Default $pythonVersion
    $poetryVersion = Read-OptionalValue -Prompt "Poetry version" -Default $poetryVersion
    $nodeVersion = Read-OptionalValue -Prompt "Node.js version" -Default $nodeVersion
    $terraformVersion = Read-OptionalValue -Prompt "Terraform version" -Default $terraformVersion
    $preCommitVersion = Read-OptionalValue -Prompt "pre-commit version" -Default $preCommitVersion
    $valeVersion = Read-OptionalValue -Prompt "Vale version" -Default $valeVersion
    $actVersion = Read-OptionalValue -Prompt "act version" -Default $actVersion

    $runProjectSetup = Read-ChoiceValue -Prompt "Run project setup" -Default $runProjectSetup -Allowed @("true", "false")
    $runValidation = Read-ChoiceValue -Prompt "Run validation" -Default $runValidation -Allowed @("true", "false")
    $runUnitTests = Read-ChoiceValue -Prompt "Run unit tests" -Default $runUnitTests -Allowed @("true", "false")
    $runBuild = Read-ChoiceValue -Prompt "Run build" -Default $runBuild -Allowed @("true", "false")
    $runIntegrationTests = Read-ChoiceValue -Prompt "Run integration tests" -Default $runIntegrationTests -Allowed @("true", "false")
}

$plan = @"
Planned actions
---------------
Mode:                $mode
Windows repo:        $RepoRoot
Repo origin:         $repoOriginUrl
WSL distro:          $distro
WSL repo root:       $wslRepoRoot
Preferred WSL user:  $defaultLinuxUser
Docker strategy:     $dockerStrategy

Versions
--------
asdf:                $($defaults["ASDF_VERSION"])
python:              $pythonVersion
poetry:              $poetryVersion
nodejs:              $nodeVersion
terraform:           $terraformVersion
pre-commit:          $preCommitVersion
vale:                $valeVersion
act:                 $actVersion

Behaviour
---------
run project setup:   $runProjectSetup
run validation:      $runValidation
run unit tests:      $runUnitTests
run build:           $runBuild
run integration:     $runIntegrationTests
"@

Write-Host ""
Write-Host $plan -ForegroundColor Cyan

if (-not (Read-YesNo -Prompt "Continue?" -Default $false)) {
    Write-Host "Cancelled."
    exit 0
}

Ensure-WSLAndDistro -Distro $distro -Mode $mode
$wslAuth = Ensure-WSLUser -Distro $distro -PreferredUser $defaultLinuxUser -Mode $mode

$wslRepoPath = "$wslRepoRoot/$repoName"

$repoOriginUrlQ = ConvertTo-BashSingleQuoted $repoOriginUrl
$wslRepoRootQ = ConvertTo-BashSingleQuoted $wslRepoRoot
$wslRepoPathQ = ConvertTo-BashSingleQuoted $wslRepoPath
$linuxUserQ = ConvertTo-BashSingleQuoted $wslAuth.User

if ($mode -eq "create") {
    $prepareTemplate = @'
set -euo pipefail

WSL_REPO_ROOT=__WSL_REPO_ROOT__
LINUX_USER=__LINUX_USER__

mkdir -p "$WSL_REPO_ROOT"
chown "$LINUX_USER:$LINUX_USER" "$WSL_REPO_ROOT"

if ! command -v git >/dev/null 2>&1; then
  apt update
  apt install -y git ca-certificates
fi
'@

    $prepareScript = $prepareTemplate.
        Replace("__WSL_REPO_ROOT__", $wslRepoRootQ).
        Replace("__LINUX_USER__", $linuxUserQ)

    Invoke-WSLScript -Distro $distro -User "root" -ScriptText $prepareScript | Out-Null

    $cloneTemplate = @'
set -euo pipefail

REPO_URL=__REPO_URL__
WSL_REPO_PATH=__WSL_REPO_PATH__

if [ -d "$WSL_REPO_PATH/.git" ]; then
  git -C "$WSL_REPO_PATH" pull --ff-only
else
  if [ -e "$WSL_REPO_PATH" ]; then
    echo "Target path exists but is not a git repo: $WSL_REPO_PATH" >&2
    exit 1
  fi
  git clone "$REPO_URL" "$WSL_REPO_PATH"
fi
'@

    $cloneScript = $cloneTemplate.
        Replace("__REPO_URL__", $repoOriginUrlQ).
        Replace("__WSL_REPO_PATH__", $wslRepoPathQ)

    Invoke-WSLScript -Distro $distro -User $wslAuth.User -ScriptText $cloneScript | Out-Null
}
else {
    $checkTemplate = @'
set -euo pipefail
WSL_REPO_PATH=__WSL_REPO_PATH__
[ -d "$WSL_REPO_PATH/.git" ]
'@

    $checkCloneScript = $checkTemplate.Replace("__WSL_REPO_PATH__", $wslRepoPathQ)
    Invoke-WSLScript -Distro $distro -User $wslAuth.User -ScriptText $checkCloneScript | Out-Null
}

$bootstrapTemplate = @'
set -euo pipefail

export DEVENV_MODE=__MODE__
export DEVENV_PYTHON_VERSION=__PYTHON_VERSION__
export DEVENV_POETRY_VERSION=__POETRY_VERSION__
export DEVENV_NODE_VERSION=__NODE_VERSION__
export DEVENV_TERRAFORM_VERSION=__TERRAFORM_VERSION__
export DEVENV_PRECOMMIT_VERSION=__PRECOMMIT_VERSION__
export DEVENV_VALE_VERSION=__VALE_VERSION__
export DEVENV_ACT_VERSION=__ACT_VERSION__
export DEVENV_DOCKER_STRATEGY=__DOCKER_STRATEGY__
export DEVENV_RUN_PROJECT_SETUP=__RUN_PROJECT_SETUP__
export DEVENV_RUN_VALIDATION=__RUN_VALIDATION__
export DEVENV_RUN_UNIT_TESTS=__RUN_UNIT_TESTS__
export DEVENV_RUN_BUILD=__RUN_BUILD__
export DEVENV_RUN_INTEGRATION_TESTS=__RUN_INTEGRATION_TESTS__
export DEVENV_SUDO_PASSWORD_B64=__SUDO_PASSWORD_B64__

cd __WSL_REPO_PATH__
chmod +x devenv/platforms/wsl-ubuntu/bootstrap.sh
bash devenv/platforms/wsl-ubuntu/bootstrap.sh
'@

$bootstrapScript = $bootstrapTemplate.
    Replace("__MODE__", (ConvertTo-BashSingleQuoted $mode)).
    Replace("__PYTHON_VERSION__", (ConvertTo-BashSingleQuoted $pythonVersion)).
    Replace("__POETRY_VERSION__", (ConvertTo-BashSingleQuoted $poetryVersion)).
    Replace("__NODE_VERSION__", (ConvertTo-BashSingleQuoted $nodeVersion)).
    Replace("__TERRAFORM_VERSION__", (ConvertTo-BashSingleQuoted $terraformVersion)).
    Replace("__PRECOMMIT_VERSION__", (ConvertTo-BashSingleQuoted $preCommitVersion)).
    Replace("__VALE_VERSION__", (ConvertTo-BashSingleQuoted $valeVersion)).
    Replace("__ACT_VERSION__", (ConvertTo-BashSingleQuoted $actVersion)).
    Replace("__DOCKER_STRATEGY__", (ConvertTo-BashSingleQuoted $dockerStrategy)).
    Replace("__RUN_PROJECT_SETUP__", (ConvertTo-BashSingleQuoted $runProjectSetup)).
    Replace("__RUN_VALIDATION__", (ConvertTo-BashSingleQuoted $runValidation)).
    Replace("__RUN_UNIT_TESTS__", (ConvertTo-BashSingleQuoted $runUnitTests)).
    Replace("__RUN_BUILD__", (ConvertTo-BashSingleQuoted $runBuild)).
    Replace("__RUN_INTEGRATION_TESTS__", (ConvertTo-BashSingleQuoted $runIntegrationTests)).
    Replace("__SUDO_PASSWORD_B64__", (ConvertTo-BashSingleQuoted $wslAuth.PasswordB64)).
    Replace("__WSL_REPO_PATH__", $wslRepoPathQ)

Invoke-WSLScript -Distro $distro -User $wslAuth.User -ScriptText $bootstrapScript
Write-Host ""
Write-Host "Done. WSL repo: $wslRepoPath" -ForegroundColor Green
Write-Host "Reports: $wslRepoPath/devenv/reports" -ForegroundColor Green