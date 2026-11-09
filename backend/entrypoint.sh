#!/bin/sh
set -e

# Ensure uploads directory exists inside persistent volume
mkdir -p /data/uploads/resource-images 2>/dev/null || true

# Run database migrations to ensure schema is at head
echo "Applying database migrations..."
alembic upgrade head
echo "Database migrations applied successfully."

exec "$@"
