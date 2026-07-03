#!/bin/bash
set -e

BACKUP_DIR="/tmp/docker_logs_backup"
DATE=$(date +%Y-%m-%d_%H-%M-%S)
ARCHIVE_NAME="emailagg_logs_$DATE.tar.gz"

# Create temp dir
mkdir -p "$BACKUP_DIR"

# Copy docker logs preserving path
sudo cp --parents /var/lib/docker/containers/*/*.log* "$BACKUP_DIR" 2>/dev/null || true

# Zip them up
cd "$BACKUP_DIR"
sudo tar -czf "$ARCHIVE_NAME" var/lib/docker/containers/ || true

# Upload using rclone
sudo rclone copy "$ARCHIVE_NAME" gdrive:EmailAgg_Logs/

# Cleanup
cd /
sudo rm -rf "$BACKUP_DIR"
