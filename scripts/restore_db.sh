#!/usr/bin/env bash
# ClinicVoice PostgreSQL Automated Restore Script (Linux / macOS)
# Verifies recovery drill from backups per DPDP Act standards.

set -euo pipefail

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <path_to_backup_file>"
    exit 1
fi

BACKUP_FILE="$1"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-clinicvoice_db}"
DB_USER="${DB_USER:-clinicvoice}"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file '$BACKUP_FILE' not found."
    exit 1
fi

echo "============================================================"
echo "  CLINICVOICE SECURE DATABASE RESTORE DRILL (DPDP ACT)      "
echo "============================================================"
echo "Source File: $BACKUP_FILE"
echo "Target DB  : $DB_NAME on $DB_HOST:$DB_PORT"

if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "postgres"; then
    CONTAINER=$(docker ps --format '{{.Names}}' | grep "postgres" | head -n1)
    echo "Restoring via Docker container '$CONTAINER'..."
    docker exec -i "$CONTAINER" pg_restore -U "$DB_USER" -d "$DB_NAME" --clean --if-exists < "$BACKUP_FILE"
else
    echo "Restoring via local pg_restore..."
    pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" --clean --if-exists -v "$BACKUP_FILE"
fi

echo "[SUCCESS] Database restored successfully from: $BACKUP_FILE"
