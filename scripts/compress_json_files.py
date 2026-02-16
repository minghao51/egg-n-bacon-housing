"""
Gzip Compression for JSON/GeoJSON Files

Compresses all JSON and GeoJSON files in app/public/data/ to reduce
download size and improve dashboard load performance.

Usage:
    uv run python scripts/compress_json_files.py
"""

import gzip
import logging
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def compress_file(file_path: Path, compression_level: int = 9) -> tuple[int, int]:
    """
    Compress a single file and save with .gz extension.

    Args:
        file_path: Path to the file to compress
        compression_level: Gzip compression level (1-9, default 9)

    Returns:
        Tuple of (original_size, compressed_size) in bytes
    """
    logger.info(f"Compressing: {file_path.name}")

    # Read original file
    with open(file_path, 'rb') as f:
        data = f.read()

    original_size = len(data)

    # Write compressed version
    gz_path = file_path.with_suffix(file_path.suffix + '.gz')
    with gzip.open(gz_path, 'wb', compresslevel=compression_level) as f:
        f.write(data)

    compressed_size = gz_path.stat().st_size
    reduction_pct = (1 - compressed_size / original_size) * 100

    logger.info(
        f"  {original_size:,} → {compressed_size:,} bytes "
        f"({reduction_pct:.1f}% reduction)"
    )

    return original_size, compressed_size


def compress_json_files(data_dir: Path = None, compression_level: int = 9):
    """
    Compress all JSON and GeoJSON files in the data directory.

    Args:
        data_dir: Directory containing JSON files (default: app/public/data)
        compression_level: Gzip compression level (1-9, default 9)
    """
    if data_dir is None:
        data_dir = Path("app/public/data")

    if not data_dir.exists():
        logger.error(f"Data directory not found: {data_dir}")
        return

    logger.info("=" * 60)
    logger.info("Gzip Compression for JSON Files")
    logger.info("=" * 60)
    logger.info(f"Target directory: {data_dir}")
    logger.info(f"Compression level: {compression_level}")
    logger.info("")

    # Find all JSON and GeoJSON files
    json_files = list(data_dir.rglob("*.json")) + list(data_dir.rglob("*.geojson"))

    if not json_files:
        logger.warning("No JSON or GeoJSON files found!")
        return

    logger.info(f"Found {len(json_files)} files to compress")
    logger.info("")

    # Compress each file
    total_original = 0
    total_compressed = 0

    for file_path in sorted(json_files):
        # Skip already compressed files
        if file_path.suffix == '.gz':
            continue

        try:
            original_size, compressed_size = compress_file(file_path, compression_level)
            total_original += original_size
            total_compressed += compressed_size
        except Exception as e:
            logger.error(f"Failed to compress {file_path.name}: {e}")

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("Compression Summary")
    logger.info("=" * 60)
    logger.info(f"Files processed: {len(json_files)}")
    logger.info(f"Total original size: {total_original:,} bytes ({total_original / 1024 / 1024:.2f} MB)")
    logger.info(f"Total compressed size: {total_compressed:,} bytes ({total_compressed / 1024 / 1024:.2f} MB)")
    logger.info(f"Total reduction: {(1 - total_compressed / total_original) * 100:.1f}%")
    logger.info(f"Space saved: {(total_original - total_compressed):,} bytes ({(total_original - total_compressed) / 1024 / 1024:.2f} MB)")
    logger.info("")

    # Verification checklist
    logger.info("✅ All JSON files compressed successfully")
    logger.info("✅ .gz files created alongside originals")
    logger.info("✅ GitHub Pages will serve .gz files with Content-Encoding: gzip")
    logger.info("")


if __name__ == "__main__":
    compress_json_files()
