#!/bin/bash
# Sync markdown files from docs/ to app/src/content/analytics/
# Also creates symlinks for data/analysis so relative image paths work

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCS_DIR="$PROJECT_ROOT/docs/analytics"
APP_CONTENT_DIR="$PROJECT_ROOT/app/src/content/analytics"
DATA_ANALYSIS_DIR="$PROJECT_ROOT/data/analysis"
APP_SRC_DIR="$PROJECT_ROOT/app/src"

echo "Syncing analytics markdown files..."

# Create app content directory if it doesn't exist
mkdir -p "$APP_CONTENT_DIR"

# Clean up old .md files first (ensures deleted files are removed)
rm -f "$APP_CONTENT_DIR"/*.md 2>/dev/null || true
echo "🧹 Cleaned up old markdown files from $APP_CONTENT_DIR/"

# Copy all .md files from docs/analytics to app content
cp -r "$DOCS_DIR"/*.md "$APP_CONTENT_DIR/" 2>/dev/null || true

# Create symlink in app/src/data -> ../../data so relative paths work
# This makes ../../data/analysis in markdown files resolve correctly
if [ ! -L "$APP_SRC_DIR/data" ]; then
    ln -s "../../data" "$APP_SRC_DIR/data"
    echo "✅ Created symlink: app/src/data -> ../../data"
fi

echo "✅ Synced $(ls -1 "$APP_CONTENT_DIR"/*.md 2>/dev/null | wc -l | tr -d ' ') markdown files to app/src/content/analytics/"
