#requires -RunAsAdministrator
$ErrorActionPreference = "Stop"

Write-Host "SmartBuild Docker repair" -ForegroundColor Cyan
Write-Host "Stopping Docker Desktop processes..."
Get-Process | Where-Object {
    $_.ProcessName -like "Docker Desktop*" -or
    $_.ProcessName -like "com.docker*" -or
    $_.ProcessName -eq "docker-sandbox"
} | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host "Enabling Windows features required by Docker Desktop..."
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

Write-Host "Enabling services used by WSL and Docker..."
Set-Service -Name LxssManager -StartupType Manual
Set-Service -Name vmcompute -StartupType Manual
Set-Service -Name com.docker.service -StartupType Manual

Start-Service -Name LxssManager -ErrorAction SilentlyContinue
Start-Service -Name vmcompute -ErrorAction SilentlyContinue
Start-Service -Name com.docker.service -ErrorAction SilentlyContinue

Write-Host "Updating WSL. This may take a few minutes..."
wsl.exe --update
wsl.exe --set-default-version 2

$dockerDesktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
if (Test-Path -LiteralPath $dockerDesktop) {
    Write-Host "Starting Docker Desktop..."
    Start-Process -FilePath $dockerDesktop
}

Write-Host "Waiting for Docker daemon..."
$deadline = (Get-Date).AddMinutes(5)
do {
    Start-Sleep -Seconds 5
    cmd.exe /c "docker info >nul 2>nul"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Docker is ready." -ForegroundColor Green
        exit 0
    }
    Write-Host "Still waiting..."
} while ((Get-Date) -lt $deadline)

Write-Host "Docker Desktop did not become ready before timeout. Restart Windows and run Docker Desktop again." -ForegroundColor Yellow
exit 1
