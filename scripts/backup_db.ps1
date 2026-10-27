# ClinicVoice PostgreSQL Automated Backup Script (Windows PowerShell)
# Adheres to DPDP Act 2023 business continuity & disaster recovery specifications.

param (
    [string]$BackupDir = "backups",
    [string]$DbHost = "localhost",
    [string]$DbPort = "5432",
    [string]$DbName = "clinicvoice_db",
    [string]$DbUser = "clinicvoice"
)

$ErrorActionPreference = "Stop"

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

$OutputFile = Join-Path $BackupDir "clinicvoice_backup_$Timestamp.sql"

Write-Host "============================================================"
Write-Host "   CLINICVOICE SECURE DATABASE BACKUP (DPDP ACT RECOVERY)   "
Write-Host "============================================================"
Write-Host "Database  : $DbName on $DbHost`:$DbPort"
Write-Host "Target    : $OutputFile"

try {
    # If Docker container is running, use docker exec; else standard pg_dump
    $DockerRunning = docker ps --filter "name=postgres" --format "{{.Names}}" 2>$null
    if ($DockerRunning -match "postgres") {
        Write-Host "Executing pg_dump via Docker container '$DockerRunning'..."
        docker exec -t $DockerRunning pg_dump -U $DbUser -d $DbName -F c > $OutputFile
    } else {
        Write-Host "Executing local pg_dump..."
        pg_dump -h $DbHost -p $DbPort -U $DbUser -F c -b -v -f $OutputFile $DbName
    }

    Write-Host "[SUCCESS] Backup created successfully: $OutputFile" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] Backup failed: $_" -ForegroundColor Red
    exit 1
}
