$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
}

cmd.exe /c "docker info >nul 2>nul"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker daemon is not ready. Run scripts\fix-docker-windows.ps1 as Administrator first." -ForegroundColor Yellow
    exit 1
}

docker compose up --build
