#!/bin/bash
# Enhanced School Impact Analysis - Complete Pipeline
# Runs all analysis modules in sequence

set -e  # Exit on error

echo "========================================="
echo "ENHANCED SCHOOL IMPACT ANALYSIS"
echo "========================================="

echo -e "\n[1/3] Spatial Cross-Validation..."
uv run python scripts/analytics/analysis/school/analyze_school_spatial_cv.py

echo -e "\n[2/3] Causal Inference (RDD)..."
uv run python scripts/analytics/analysis/school/analyze_school_rdd.py

echo -e "\n[3/3] Segmentation & Interactions..."
uv run python scripts/analytics/analysis/school/analyze_school_segmentation.py

echo -e "\n========================================="
echo "ANALYSIS COMPLETE"
echo "========================================="
echo -e "\nResults:"
echo "  - data/analytics/school_spatial_cv/"
echo "  - data/analytics/school_rdd/"
echo "  - data/analytics/school_segmentation/"
