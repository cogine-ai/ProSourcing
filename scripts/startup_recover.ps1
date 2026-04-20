$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir

Set-Location $projectRoot

$logDir = Join-Path $projectRoot "logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

$pythonCandidates = @(
    "python",
    "py"
)

$pythonCmd = $null
foreach ($candidate in $pythonCandidates) {
    try {
        & $candidate --version *> $null
        if ($LASTEXITCODE -eq 0) {
            $pythonCmd = $candidate
            break
        }
    } catch {
    }
}

if (-not $pythonCmd) {
    throw "Python not found in PATH."
}

& $pythonCmd (Join-Path $scriptDir "startup_recover.py") @args
exit $LASTEXITCODE
