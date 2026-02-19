#!/usr/bin/env python3
"""
L4 Analysis Pipeline

Orchestrates execution of all analysis scripts in scripts/analysis/ and generates a summary report.

Pipeline phases:
1. EDA Phase: Quick investment analysis summaries (data quality, appreciation, yields, scoring)
2. Analysis Phase: Deep-dive analysis scripts (spatial, market, amenity, etc.)
3. Report Generation: Summary markdown report

Usage:
    uv run python core/pipeline/L4_analysis.py
"""  # noqa: N999

import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.core.config import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SCRIPT_ORDER = [
    "analyze_spatial_hotspots",
    "analyze_spatial_autocorrelation",
    "analyze_h3_clusters",
    "analyze_hdb_rental_market",
    "analyze_amenity_impact",
    "analyze_policy_impact",
    "analyze_lease_decay",
    "analyze_feature_importance",
    "market_segmentation_advanced",
]


def run_eda_phase() -> dict:
    """Run EDA phase before analysis scripts."""
    logger.info("=" * 60)
    logger.info("PHASE 1: EXPLORATORY DATA ANALYSIS")
    logger.info("=" * 60)

    try:
        from scripts.analytics.analysis.market.analyze_investment_eda import run_eda

        run_eda()
        logger.info("✅ EDA Phase Complete")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"❌ EDA Phase Failed: {e}")
        return {"status": "failed", "error": str(e)}


def discover_scripts() -> list:
    """Discover all analyze scripts in scripts/analysis/."""
    scripts_dir = Config.ANALYSIS_SCRIPTS_DIR

    if not scripts_dir.exists():
        logger.error(f"Scripts directory not found: {scripts_dir}")
        return []

    scripts = []
    for f in sorted(scripts_dir.glob("analyze_*.py")):
        scripts.append(f.name)

    logger.info(f"Discovered {len(scripts)} analysis scripts")
    return scripts


def run_script(script_name: str) -> dict:
    """Run a single analysis script and capture results."""
    if not script_name.endswith(".py"):
        script_name_with_ext = f"{script_name}.py"
    else:
        script_name_with_ext = script_name

    script_path = Config.ANALYSIS_SCRIPTS_DIR / script_name_with_ext

    logger.info(f"Running {script_name}...")

    start_time = datetime.now()

    env = {**__import__("os").environ, "PYTHONPATH": str(Config.BASE_DIR)}

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(Config.BASE_DIR),
            env=env,
        )

        duration = (datetime.now() - start_time).total_seconds()

        if result.returncode == 0:
            output = result.stdout.strip()
            summary = parse_json_output(output)

            logger.info(f"  ✓ {script_name} completed in {duration:.1f}s")

            return {
                "script": script_name,
                "status": "success",
                "duration_seconds": round(duration, 2),
                "key_findings": summary.get("key_findings", []),
                "outputs": summary.get("outputs", []),
                "error": None,
            }
        else:
            logger.error(f"  ✗ {script_name} failed")
            logger.error(f"  stderr: {result.stderr}")

            return {
                "script": script_name,
                "status": "failed",
                "duration_seconds": round(duration, 2),
                "key_findings": [],
                "outputs": [],
                "error": result.stderr.strip()[:500],
            }

    except subprocess.TimeoutExpired:
        duration = (datetime.now() - start_time).total_seconds()
        logger.error(f"  ✗ {script_name} timed out after {duration:.1f}s")

        return {
            "script": script_name,
            "status": "timeout",
            "duration_seconds": round(duration, 2),
            "key_findings": [],
            "outputs": [],
            "error": "Script timed out after 300 seconds",
        }

    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        logger.error(f"  ✗ {script_name} error: {e}")

        return {
            "script": script_name,
            "status": "error",
            "duration_seconds": round(duration, 2),
            "key_findings": [],
            "outputs": [],
            "error": str(e)[:500],
        }


def parse_json_output(output: str) -> dict:
    """Parse JSON summary from script output."""
    for line in output.split("\n"):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return {}


def generate_report(results: list, duration: float) -> str:
    """Generate markdown summary report."""
    succeeded = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] != "success"]

    report = f"""# L4 Analysis Pipeline Summary Report

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Duration:** {duration:.1f} seconds

## Execution Summary

| Metric | Value |
|--------|-------|
| Scripts Discovered | {len(results)} |
| Scripts Executed | {len(results)} |
| Succeeded | {len(succeeded)} |
| Failed | {len(failed)} |

## Script Results

"""
    for result in results:
        status_icon = "✅" if result["status"] == "success" else "❌"

        report += f"""### {result["script"]}
- **Status:** {status_icon} {result["status"].upper()}
- **Duration:** {result["duration_seconds"]:.1f}s
"""

        if result["key_findings"]:
            report += "- **Key Findings:**\n"
            for finding in result["key_findings"][:5]:
                report += f"  - {finding}\n"

        if result["outputs"]:
            report += "- **Outputs:**\n"
            for output in result["outputs"][:3]:
                report += f"  - `{output}`\n"

        if result["error"]:
            report += f"- **Error:** `{result['error'][:200]}...`\n"

        report += "\n"

    if succeeded:
        report += """## Aggregate Insights

"""
        all_findings = []
        for r in succeeded:
            all_findings.extend(r.get("key_findings", []))

        for finding in all_findings[:10]:
            report += f"- {finding}\n"

        report += "\n"

    report += """---

*Report generated by L4_analysis.py*
"""

    return report


def main():
    start_time = datetime.now()

    logger.info("=" * 60)
    logger.info("L4 ANALYSIS PIPELINE")
    logger.info("=" * 60)

    # Phase 1: Run EDA
    logger.info("-" * 60)
    run_eda_phase()
    logger.info("-" * 60)

    Config.ANALYSIS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    scripts = discover_scripts()

    if not scripts:
        logger.error("No analysis scripts found")
        return

    logger.info(f"Scripts to run: {len(scripts)}")

    results = []
    for script_name in scripts:
        if script_name.endswith(".py"):
            script_name = script_name[:-3]
        result = run_script(script_name)
        results.append(result)

    pipeline_duration = (datetime.now() - start_time).total_seconds()

    report = generate_report(results, pipeline_duration)

    report_path = Config.L4_REPORT_PATH
    with open(report_path, "w") as f:
        f.write(report)
    logger.info(f"Saved report: {report_path}")

    succeeded = sum(1 for r in results if r["status"] == "success")
    failed = len(results) - succeeded

    logger.info("\n" + "=" * 60)
    logger.info("PIPELINE COMPLETE")
    logger.info(f"  Succeeded: {succeeded}/{len(results)}")
    logger.info(f"  Failed: {failed}/{len(results)}")
    logger.info(f"  Total Duration: {pipeline_duration:.1f}s")
    logger.info(f"  Report: {report_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
