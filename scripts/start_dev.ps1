param(
    [string]$Host = "127.0.0.1",
    [int]$Port = 8000,
    [string]$SessionBackend = "mysql",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path ".env.dev")) {
    Write-Error "Missing .env.dev in repository root. Create it from .env.example first."
}

if (-not $SkipInstall) {
    Write-Host "Installing project dependencies (editable mode)..."
    pip install -e .
}

$env:PYTHONPATH = "."
$env:ENV = "dev"
$env:SESSION_REPOSITORY_BACKEND = $SessionBackend

Write-Host "Starting API in dev mode with ENV=$($env:ENV), backend=$SessionBackend on ${Host}:${Port}"
python -m uvicorn apps.api.main:app --host $Host --port $Port --reload
