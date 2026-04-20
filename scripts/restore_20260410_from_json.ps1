param(
    [switch]$RecreateDb,
    [string]$ComposeFile = "docker-compose.yml",
    [string]$EnvFile = ".env",
    [string]$JsonPath = "scripts/full_category_data.json"
)

$ErrorActionPreference = "Stop"

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Missing required command: $Name"
    }
}

function Get-EnvValue {
    param(
        [string]$Path,
        [string]$Key,
        [string]$DefaultValue
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return $DefaultValue
    }

    $line = Get-Content -LiteralPath $Path |
        Where-Object { $_ -match "^\s*$Key=" } |
        Select-Object -First 1

    if (-not $line) {
        return $DefaultValue
    }

    return ($line -split "=", 2)[1].Trim()
}

function Invoke-Checked {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )

    Write-Host ">> $FilePath $($Arguments -join ' ')"
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE: $FilePath $($Arguments -join ' ')"
    }
}

Require-Command "docker"

$projectRoot = Split-Path -Parent $PSScriptRoot
$composePath = Join-Path $projectRoot $ComposeFile
$envPath = Join-Path $projectRoot $EnvFile
$jsonFullPath = Join-Path $projectRoot $JsonPath
$initSqlPath = Join-Path $projectRoot "scripts/init.sql"

if (-not (Test-Path -LiteralPath $composePath)) {
    throw "Compose file not found: $composePath"
}

if (-not (Test-Path -LiteralPath $jsonFullPath)) {
    throw "JSON file not found: $jsonFullPath"
}

if (-not (Test-Path -LiteralPath $initSqlPath)) {
    throw "init.sql not found: $initSqlPath"
}

$pgUser = Get-EnvValue -Path $envPath -Key "PG_USER" -DefaultValue "postgres"
$pgDb = Get-EnvValue -Path $envPath -Key "PG_DB" -DefaultValue "prosourcing"

$composeArgs = @("compose", "--env-file", $envPath, "-f", $composePath)

Write-Host ""
Write-Host "=== ProSourcing DB restore from JSON ==="
Write-Host "Project root : $projectRoot"
Write-Host "Compose file : $composePath"
Write-Host "Env file     : $envPath"
Write-Host "JSON file    : $jsonFullPath"
Write-Host "Postgres DB  : $pgDb"
Write-Host "Recreate DB  : $RecreateDb"
Write-Host ""

if ($RecreateDb) {
    Write-Host "Step 1/5: Recreating database containers and volume..."
    Invoke-Checked -FilePath "docker" -Arguments ($composeArgs + @("down", "-v"))
} else {
    Write-Host "Step 1/5: Keeping existing volume and starting services..."
}

Write-Host "Step 2/5: Starting db and backend containers..."
Invoke-Checked -FilePath "docker" -Arguments ($composeArgs + @("up", "-d", "db", "backend"))

Write-Host "Step 3/5: Waiting for PostgreSQL to become ready..."
$maxAttempts = 30
for ($i = 1; $i -le $maxAttempts; $i++) {
    & docker exec prosourcing_db pg_isready -U $pgUser -d $pgDb | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "PostgreSQL is ready."
        break
    }

    if ($i -eq $maxAttempts) {
        throw "PostgreSQL did not become ready in time."
    }

    Start-Sleep -Seconds 2
}

Write-Host "Step 4/5: Applying schema and bootstrap SQL..."
Get-Content -LiteralPath $initSqlPath | docker exec -i prosourcing_db psql -U $pgUser -d $pgDb
if ($LASTEXITCODE -ne 0) {
    throw "Failed to apply init.sql"
}

Write-Host "Step 5/5: Importing JSON data into PostgreSQL..."
Invoke-Checked -FilePath "docker" -Arguments ($composeArgs + @("exec", "-T", "backend", "python", "/app/scripts/seed_db_from_json.py"))

Write-Host ""
Write-Host "Restore completed."
Write-Host "Quick checks:"
Write-Host "  docker exec -it prosourcing_db psql -U $pgUser -d $pgDb -c `"select count(*) from algatop_categories_master;`""
Write-Host "  docker exec -it prosourcing_db psql -U $pgUser -d $pgDb -c `"select count(*) from algatop_top_category_stats;`""
