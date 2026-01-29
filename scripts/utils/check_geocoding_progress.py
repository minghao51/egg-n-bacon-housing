#!/usr/bin/env python3
"""
Quick status checker for geocoding progress.

Usage:
    python scripts/check_geocoding_progress.py

This script displays:
- Current progress (addresses processed / total)
- Percentage complete
- Estimated time remaining
- Recent errors or failures
"""

import sys
import pathlib
import re
from datetime import datetime

# Add project root to path
PROJECT_ROOT = pathlib.Path(__file__).parent.parent
LOG_DIR = PROJECT_ROOT / 'data' / 'logs'
CHECKPOINT_DIR = PROJECT_ROOT / 'data' / 'checkpoints'

def get_latest_log_file():
    """Get the most recent geocoding log file."""
    log_files = list(LOG_DIR.glob('geocoding_*.log'))
    if not log_files:
        return None
    return max(log_files, key=lambda p: p.stat().st_mtime)

def parse_log_for_progress(log_file):
    """Parse log file to extract progress information."""
    progress_lines = []
    error_lines = []
    start_time = None

    with open(log_file, 'r') as f:
        for line in f:
            # Look for progress lines
            if 'Progress:' in line and 'addresses' in line:
                progress_lines.append(line.strip())

            # Look for error lines
            if '❌ Request failed' in line or 'ERROR' in line:
                error_lines.append(line.strip())

            # Look for start time
            if 'Starting geocoding for' in line:
                # Extract timestamp
                timestamp_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                if timestamp_match:
                    start_time = datetime.strptime(timestamp_match.group(1), '%Y-%m-%d %H:%M:%S')

    return progress_lines, error_lines, start_time

def parse_progress_line(line):
    """Parse a progress line to extract count and percentage."""
    # Example: "2026-01-21 14:52:45 - INFO - Progress: 200/12166 addresses (1.6%)"
    match = re.search(r'Progress: (\d+)/(\d+) addresses \(([\d.]+)%\)', line)
    if match:
        return {
            'processed': int(match.group(1)),
            'total': int(match.group(2)),
            'percentage': float(match.group(3))
        }
    return None

def get_checkpoint_info():
    """Get information about latest checkpoint."""
    checkpoints = list(CHECKPOINT_DIR.glob('L2_housing_unique_searched_checkpoint_*.parquet'))
    if not checkpoints:
        return None

    latest_checkpoint = max(checkpoints, key=lambda p: p.stat().st_mtime)

    # Try to load checkpoint to get count
    try:
        import pandas as pd
        df = pd.read_parquet(latest_checkpoint)
        return {
            'file': latest_checkpoint.name,
            'count': len(df),
            'modified': datetime.fromtimestamp(latest_checkpoint.stat().st_mtime)
        }
    except:
        return {
            'file': latest_checkpoint.name,
            'count': 'Unknown',
            'modified': datetime.fromtimestamp(latest_checkpoint.stat().st_mtime)
        }

def format_duration(seconds):
    """Format seconds into human-readable duration."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"

def main():
    """Display geocoding progress summary."""
    print("=" * 70)
    print("📊 Geocoding Progress Check")
    print("=" * 70)

    # Check log file
    log_file = get_latest_log_file()

    if not log_file:
        print("❌ No geocoding log file found.")
        print("   Has the geocoding script been started?")
        return

    print(f"📄 Log file: {log_file.name}")
    print(f"   Last modified: {datetime.fromtimestamp(log_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Parse log for progress
    progress_lines, error_lines, start_time = parse_log_for_progress(log_file)

    if not progress_lines:
        print("⏳ No progress updates found in log.")
        print("   Script may still be initializing...")
        return

    # Get latest progress
    latest_progress = parse_progress_line(progress_lines[-1])

    if not latest_progress:
        print("⚠️  Could not parse latest progress.")
        return

    # Display progress
    print(f"📍 Latest Progress:")
    print(f"   Processed: {latest_progress['processed']:,} / {latest_progress['total']:,} addresses")
    print(f"   Complete: {latest_progress['percentage']:.1f}%")
    print()

    # Calculate ETA if we have start time
    if start_time and latest_progress['processed'] > 0:
        elapsed = (datetime.now() - start_time).total_seconds()
        rate = latest_progress['processed'] / elapsed  # addresses per second

        if rate > 0:
            remaining = latest_progress['total'] - latest_progress['processed']
            eta_seconds = remaining / rate
            eta_str = format_duration(eta_seconds)

            print(f"⏱️  Timing:")
            print(f"   Elapsed: {format_duration(elapsed)}")
            print(f"   Rate: {rate:.2f} addresses/second")
            print(f"   ETA: {eta_str}")
            print()

    # Display checkpoint info
    checkpoint_info = get_checkpoint_info()
    if checkpoint_info:
        print(f"💾 Latest Checkpoint:")
        print(f"   File: {checkpoint_info['file']}")
        print(f"   Addresses: {checkpoint_info['count']:,}" if isinstance(checkpoint_info['count'], int) else f"   Addresses: {checkpoint_info['count']}")
        print(f"   Modified: {checkpoint_info['modified'].strftime('%Y-%m-%d %H:%M:%S')}")
        print()

    # Display recent errors
    if error_lines:
        print(f"⚠️  Recent Errors (last 5):")
        for error in error_lines[-5:]:
            print(f"   {error}")
        print()
    else:
        print("✅ No errors reported")
        print()

    # Show if still running
    print("💡 To see real-time logs:")
    print(f"   tail -f {log_file}")
    print()

if __name__ == "__main__":
    main()
