<#
.SYNOPSIS
    One-line installer for ShadowPlane CLI.
.DESCRIPTION
    Run this from any PowerShell terminal:
    irm https://raw.githubusercontent.com/GOLDSTEALTH/ShadowPlane/main/install.ps1 | iex
.NOTES
    Requires: Python 3.10+, pip, git
#>

$ErrorActionPreference = "Stop"

# ── Branding ──────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ┌─────────────────────────────────────────────┐" -ForegroundColor Cyan
Write-Host "  │         ShadowPlane Installer                │" -ForegroundColor Cyan
Write-Host "  │   Autonomous Infrastructure Verification     │" -ForegroundColor Cyan
Write-Host "  └─────────────────────────────────────────────┘" -ForegroundColor Cyan
Write-Host ""

# ── Preflight checks ─────────────────────────────────────────────────────────
function Test-Command($cmd) {
    $null = Get-Command $cmd -ErrorAction SilentlyContinue
    return $?
}

Write-Host "[1/5] Checking prerequisites..." -ForegroundColor Yellow

# Python
$pythonCmd = $null
foreach ($candidate in @("python3", "python")) {
    if (Test-Command $candidate) {
        # Verify it's real Python, not the Windows Store stub
        $ver = & $candidate --version 2>&1
        if ($ver -match "Python\s+3\.(\d+)") {
            $minor = [int]$Matches[1]
            if ($minor -ge 10) {
                $pythonCmd = $candidate
                Write-Host "  [OK] $candidate ($ver)" -ForegroundColor Green
                break
            }
        }
    }
}
if (-not $pythonCmd) {
    Write-Host "  [FAIL] Python 3.10+ is required but not found." -ForegroundColor Red
    Write-Host "         Download from: https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}

# pip
$pipWorks = & $pythonCmd -m pip --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [FAIL] pip is not available." -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] pip" -ForegroundColor Green

# git
if (-not (Test-Command "git")) {
    Write-Host "  [FAIL] git is required but not found." -ForegroundColor Red
    Write-Host "         Download from: https://git-scm.com/downloads" -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] git" -ForegroundColor Green

# ── Install method: pip from git (no clone needed) ────────────────────────────
Write-Host ""
Write-Host "[2/5] Installing ShadowPlane..." -ForegroundColor Yellow

# Try PyPI first, fall back to git
$pypiInstall = $false
try {
    & $pythonCmd -m pip install shadowplane 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $pypiInstall = $true
        Write-Host "  Installed from PyPI" -ForegroundColor Green
    }
} catch {}

if (-not $pypiInstall) {
    Write-Host "  PyPI package not found, installing from GitHub..." -ForegroundColor DarkYellow
    & $pythonCmd -m pip install "git+https://github.com/GOLDSTEALTH/ShadowPlane.git" 2>&1 | ForEach-Object {
        if ($_ -match "Successfully installed") { Write-Host "  $_" -ForegroundColor Green }
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [FAIL] Installation failed." -ForegroundColor Red
        exit 1
    }
}

# ── Verify installation ──────────────────────────────────────────────────────
Write-Host ""
Write-Host "[3/5] Verifying installation..." -ForegroundColor Yellow

$cmds = @("shadowplane", "shadowplane-server", "shadowplane-engine")
$allGood = $true
foreach ($cmd in $cmds) {
    if (Test-Command $cmd) {
        Write-Host "  [OK] $cmd" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] $cmd not found in PATH" -ForegroundColor Yellow
        $allGood = $false
    }
}

# ── PATH check ────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "[4/5] Checking PATH..." -ForegroundColor Yellow

$scriptsDir = & $pythonCmd -c "import sysconfig; print(sysconfig.get_path('scripts'))" 2>&1
if ($env:PATH -notlike "*$scriptsDir*") {
    Write-Host "  [WARN] Python Scripts directory is not in PATH:" -ForegroundColor Yellow
    Write-Host "         $scriptsDir" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  To fix, run:" -ForegroundColor Yellow
    Write-Host "    [Environment]::SetEnvironmentVariable('PATH', `$env:PATH + ';$scriptsDir', 'User')" -ForegroundColor Cyan
} else {
    Write-Host "  [OK] Scripts directory is in PATH" -ForegroundColor Green
}

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "[5/5] Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "  Available commands:" -ForegroundColor White
Write-Host "    shadowplane             Run the verification pipeline" -ForegroundColor Cyan
Write-Host "    shadowplane-server      Start the MCP gateway server" -ForegroundColor Cyan
Write-Host "    shadowplane-engine      Run the enterprise engine" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Quick start:" -ForegroundColor White
Write-Host "    shadowplane --help" -ForegroundColor Cyan
Write-Host "    shadowplane --target-dir ./your-infra" -ForegroundColor Cyan
Write-Host ""
