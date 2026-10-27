# ClinicVoice PostgreSQL Automated Restore Script (Windows PowerShell)
# Verifies recovery drill from backups per DPDP Act standards.

param (
    [Parameter(Mandatory=$true)]
    [string]$BackupFile,
    [string]$DbHost = "localhost",
    [string]$DbPort = "5432",
    [string]$DbName = "clinicvoice_db",
    [string]$DbUser = "clinicvoice"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BackupFile)) {
    Write-Error "Backup file not found: $BackupFile"
    exit 1
}

Write-Host "============================================================"
Write-Host "  CLINICVOICE SECURE DATABASE RESTORE DRILL (DPDP ACT)      "
Write-Host "============================================================"
Write-Host "Source File: $BackupFile"
Write-Host "Target DB  : $DbName on $DbHost`:$DbPort"

try {
    $DockerRunning = docker ps --filter "name=postgres" --format "{{.Names}}" 2>$null
    if ($DockerRunning -match "postgres") {
        Write-Host "Restoring via Docker container '$DockerRunning'..."
        Get-Content $BackupFile | docker exec -i $DockerRunning pg_restore -U $DbUser -d $DbName --clean --if-exists
    } else {
        Write-Host "Restoring via local pg_restore..."
        pg_restore -h $DbHost -p $DbPort -U $DbUser -d $DbName --clean --if-exists -v $BackupFile
    }

    Write-Host "[SUCCESS] Database restored successfully from: $BackupFile" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] Database restore failed: $_" -ForegroundColor Red
    exit 1
}
