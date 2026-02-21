#!/bin/bash
# Sync markdown files from docs/ to app/src/content/analytics/
# Also creates symlinks for data/analytics so relative image paths work

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCS_DIR="$PROJECT_ROOT/docs/analytics"
APP_CONTENT_DIR="$PROJECT_ROOT/app/src/content/analytics"
DATA_ANALYTICS_DIR="$PROJECT_ROOT/data/analytics"
APP_SRC_DIR="$PROJECT_ROOT/app/src"

# Valid categories (space-separated list for bash 3.2 compatibility)
VALID_CATEGORIES="investment-guides market-analysis technical-reports quick-reference"

extract_category() {
  local file="$1"
  grep -m1 '^category:' "$file" | sed 's/^category: *//' | tr -d '"'"'"
}

validate_category() {
  local file="$1"
  local category=$(extract_category "$file")

  if [ -z "$category" ]; then
    echo "⚠️  Missing category in: $(basename "$file")"
    echo "   Valid categories: $VALID_CATEGORIES"
    return 1
  fi

  # Check if category is in the valid list (space-separated matching)
  local valid_cat
  for valid_cat in $VALID_CATEGORIES; do
    if [ "$category" = "$valid_cat" ]; then
      return 0
    fi
  done

  echo "⚠️  Invalid category '$category' in: $(basename "$file")"
  echo "   Valid categories: $VALID_CATEGORIES"
  return 1
}

echo "Syncing analytics markdown files..."

# Create app content directory if it doesn't exist
mkdir -p "$APP_CONTENT_DIR"

# Clean up old .mdx files first (ensures deleted files are removed)
rm -f "$APP_CONTENT_DIR"/*.mdx 2>/dev/null || true
echo "🧹 Cleaned up old markdown files from $APP_CONTENT_DIR/"

# Copy .md files from docs/analytics and rename to .mdx for Astro
# We keep source as .md for compatibility and convert to .mdx during sync
for md_file in "$DOCS_DIR"/*.md; do
    if [ -f "$md_file" ]; then
        filename=$(basename "$md_file" .md)
        cp "$md_file" "$APP_CONTENT_DIR/${filename}.mdx"
    fi
done

# Skip validation if no files copied
if ! ls "$APP_CONTENT_DIR"/*.mdx 2>/dev/null | grep -q .; then
  echo "⚠️  No markdown files found in $APP_CONTENT_DIR/"
  exit 1
fi

# Validate categories in copied files
echo "🔍 Validating categories..."
invalid_count=0
for file in "$APP_CONTENT_DIR"/*.mdx; do
  if ! validate_category "$file"; then
    invalid_count=$((invalid_count + 1))
  fi
done

if [ $invalid_count -gt 0 ]; then
  echo "⚠️  Found $invalid_count file(s) with invalid/missing categories"
  exit 1
fi

echo "✅ All categories validated successfully"

# Fix image paths: ../../data/ -> /egg-n-bacon-housing/data/
# Images are now in app/public/data/analysis/ and served from base path by Astro
echo "🔧 Fixing image paths in analytics documents..."
path_count=0
for file in "$APP_CONTENT_DIR"/*.mdx; do
    if grep -q "../../data/" "$file"; then
        # Use cross-platform sed with backup file
        # Change relative paths to absolute paths (from production base path)
        sed -i.bak 's|](../../data/|](/egg-n-bacon-housing/data/|g' "$file"
        rm -f "${file}.bak"
        path_count=$((path_count + 1))
    fi
done

if [ $path_count -gt 0 ]; then
    echo "✅ Fixed image paths in $path_count document(s)"
fi

# Remove Astro component import statements from MDX files
# Astro MDX doesn't support importing .astro components, so these just show as text
echo "🔧 Removing Astro component imports from MDX files..."
import_count=0
for file in "$APP_CONTENT_DIR"/*.mdx; do
    if grep -q "^import.*from '@/components/analytics/" "$file"; then
        # Remove lines that import from @/components/analytics/
        sed -i.bak "/^import.*from '@\/components\/analytics\//d" "$file"
        rm -f "${file}.bak"
        import_count=$((import_count + 1))
    fi
done

if [ $import_count -gt 0 ]; then
    echo "✅ Removed component imports from $import_count MDX file(s)"
fi

# Remove unused Astro component tags from MDX files
# Since we removed the imports, we need to remove the component tags too
echo "🔧 Removing unused Astro component tags from MDX files..."
component_count=0
for file in "$APP_CONTENT_DIR"/*.mdx; do
    # Remove inline and multi-line component tags using perl
    # Handle: <StatCallout ... /> (multi-line), <ImplicationBox>...</ImplicationBox>, etc.
    perl -i.bak -0777 -pe '
        s/<StatCallout\s.*?\/>//gs;
        s/<ImplicationBox\s.*?<\/ImplicationBox>//gs;
        s/<Scenario\s.*?<\/Scenario>//gs;
        s/<DecisionChecklist\s.*?<\/DecisionChecklist>//gs;
        s/<Tooltip[^>]*>.*?<\/Tooltip>//gs;
    ' "$file"
    rm -f "${file}.bak"
    component_count=$((component_count + 1))
done

if [ $component_count -gt 0 ]; then
    echo "✅ Removed component tags from $component_count MDX file(s)"
fi

# Escape < symbols that break MDX parsing (e.g., <60, <$1500)
# MDX interprets < as JSX syntax, so we need to escape these in certain contexts
echo "🔧 Escaping MDX-incompatible angle brackets..."
bracket_count=0
for file in "$APP_CONTENT_DIR"/*.mdx; do
    if grep -qE '<[0-9$]+|[(<][[:space:]]*<\$' "$file"; then
        # Use sed with proper escaping - safer than perl for special chars
        # First handle patterns like " (<$1500" - escape the <
        sed -i.bak -E 's/\([[:space:]]*<[[:space:]]*\$?/\(\&lt;/g' "$file"
        # Then handle remaining patterns like <60, <$1500 not preceded by valid HTML tag chars
        sed -i.bak -E 's/(^|[^a-zA-Z/:&])<([[:space:]]*\$?[0-9,]+)/\1\&lt;\2/g' "$file"
        rm -f "${file}.bak"
        bracket_count=$((bracket_count + 1))
    fi
done

if [ $bracket_count -gt 0 ]; then
    echo "✅ Fixed angle brackets in $bracket_count MDX file(s)"
fi

# Create symlink in app/src/data -> ../../data so relative paths work
# This makes ../../data/analytics in markdown files resolve correctly
if [ ! -L "$APP_SRC_DIR/data" ] && [ ! -e "$APP_SRC_DIR/data" ]; then
    ln -s "../../data" "$APP_SRC_DIR/data"
    echo "✅ Created symlink: app/src/data -> ../../data"
elif [ ! -L "$APP_SRC_DIR/data" ] && [ -e "$APP_SRC_DIR/data" ]; then
    echo "⚠️  app/src/data exists but is not a symlink, skipping"
fi

# Sync analytics images from data/analytics to app/public/data/analysis
DATA_ANALYTICS_SRC="$PROJECT_ROOT/data/analytics"
APP_ANALYTICS_DEST="$PROJECT_ROOT/app/public/data/analysis"

if [ -d "$DATA_ANALYTICS_SRC" ]; then
    echo "🖼️  Syncing analytics images..."
    mkdir -p "$APP_ANALYTICS_DEST"

    # Use find to copy only image files, preserving directory structure
    find "$DATA_ANALYTICS_SRC" -type f \( -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" \) | while read img; do
        rel_path="${img#$DATA_ANALYTICS_SRC/}"
        dest_dir="$APP_ANALYTICS_DEST/$(dirname "$rel_path")"
        mkdir -p "$dest_dir"
        cp "$img" "$dest_dir/"
    done

    # Clean up orphaned files in destination (files not in source)
    if command -v rsync &> /dev/null; then
        rsync -av --delete --include='*/' --include='*.png' --include='*.jpg' --include='*.jpeg' \
              --exclude='*' "$DATA_ANALYTICS_SRC/" "$APP_ANALYTICS_DEST/" 2>/dev/null || true
    fi

    img_count=$(find "$APP_ANALYTICS_DEST" -type f \( -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" \) | wc -l | tr -d ' ')
    echo "✅ Synced $img_count analytics images"
fi

file_count=$(ls -1 "$APP_CONTENT_DIR"/*.mdx 2>/dev/null | wc -l | tr -d ' ')
echo "✅ Synced $file_count markdown files to app/src/content/analytics/"
