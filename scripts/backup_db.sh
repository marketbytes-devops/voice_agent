#!/usr/bin/env bash
# ClinicVoice PostgreSQL Automated Backup Script (Linux / macOS)
# Adheres to DPDP Act 2023 business continuity & disaster recovery specifications.

set -euo pipefail

BACKUP_DIR="${1:-backups}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-clinicvoice_db}"
DB_USER="${DB_USER:-clinicvoice}"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
mkdir -p "$BACKUP_DIR"
OUTPUT_FILE="$BACKUP_DIR/clinicvoice_backup_$TIMESTAMP.dump"

echo "============================================================"
echo "   CLINICVOICE SECURE DATABASE BACKUP (DPDP ACT RECOVERY)   "
echo "============================================================"
echo "Database  : $DB_NAME on $DB_HOST:$DB_PORT"
echo "Target    : $OUTPUT_FILE"

if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "postgres"; then
    CONTAINER=$(docker ps --format '{{.Names}}' | grep "postgres" | head -n1)
    echo "Executing pg_dump via Docker container '$CONTAINER'..."
    docker exec -t "$CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" -F c > "$OUTPUT_FILE"
else
    echo "Executing local pg_dump..."
    pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -F c -b -f "$OUTPUT_FILE" "$DB_NAME"
fi

echo "[SUCCESS] Backup created successfully: $OUTPUT_FILE"
