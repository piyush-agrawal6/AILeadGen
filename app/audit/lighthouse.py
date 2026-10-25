import asyncio
import json
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Optional
from app.config.settings import get_settings
from app.database.models import LighthouseResult

logger = logging.getLogger("leadengine.audit.lighthouse")
REPORTS_DIR = Path("data/lighthouse")


def find_lighthouse_executable() -> Optional[str]:
    """Find lighthouse executable in node_modules or system PATH."""
    settings = get_settings()
    configured_cmd = settings.lighthouse_command or settings.audit.lighthouse_command

    # 1. Check local node_modules
    local_cmd = Path("node_modules/.bin/lighthouse.cmd")
    local_sh = Path("node_modules/.bin/lighthouse")
    if os.name == "nt" and local_cmd.exists():
        return str(local_cmd.resolve())
    elif local_sh.exists():
        return str(local_sh.resolve())

    # 2. Check configured command
    if configured_cmd:
        which_path = shutil.which(configured_cmd)
        if which_path:
            return which_path

    # 3. Check standard path
    standard_which = shutil.which("lighthouse")
    if standard_which:
        return standard_which

    return None


async def run_lighthouse_audit(
    business_id: int,
    target_url: str,
    timeout_seconds: int = 90,
) -> Optional[LighthouseResult]:
    """Execute local Lighthouse CLI against target URL, parse metrics and scores, and save JSON report."""
    lh_bin = find_lighthouse_executable()
    if not lh_bin:
        logger.warning("Lighthouse executable not found. Skipping Lighthouse audit.")
        return None

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_file = REPORTS_DIR / f"{business_id}.json"

    # Command line arguments for headless chrome and fast auditing
    cmd = [
        lh_bin,
        target_url,
        "--output=json",
        f"--output-path={report_file}",
        "--chrome-flags=--headless --no-sandbox --disable-gpu --disable-dev-shm-usage",
        "--only-categories=performance,seo,accessibility,best-practices",
        "--quiet",
    ]

    logger.info(f"Running Lighthouse for business #{business_id} ({target_url})...")
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            logger.warning(f"Lighthouse audit timed out after {timeout_seconds}s for #{business_id}")
            return None

        if not report_file.exists():
            err_msg = stderr.decode("utf-8", errors="replace")[:200]
            logger.warning(f"Lighthouse report not generated for #{business_id}: {err_msg}")
            return None

        # Parse JSON output
        with open(report_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        categories = data.get("categories", {})
        audits = data.get("audits", {})

        perf_cat = categories.get("performance", {})
        seo_cat = categories.get("seo", {})
        a11y_cat = categories.get("accessibility", {})
        bp_cat = categories.get("best-practices", {})

        # Extract normalized 0-100 scores
        perf_score = round(perf_cat.get("score", 0) * 100, 1) if perf_cat.get("score") is not None else None
        seo_score = round(seo_cat.get("score", 0) * 100, 1) if seo_cat.get("score") is not None else None
        a11y_score = round(a11y_cat.get("score", 0) * 100, 1) if a11y_cat.get("score") is not None else None
        bp_score = round(bp_cat.get("score", 0) * 100, 1) if bp_cat.get("score") is not None else None

        # Core Web Vitals / performance metrics
        lcp_val = audits.get("largest-contentful-paint", {}).get("numericValue")
        cls_val = audits.get("cumulative-layout-shift", {}).get("numericValue")
        tbt_val = audits.get("total-blocking-time", {}).get("numericValue")
        fcp_val = audits.get("first-contentful-paint", {}).get("numericValue")
        si_val = audits.get("speed-index", {}).get("numericValue")

        result = LighthouseResult(
            business_id=business_id,
            performance_score=perf_score,
            seo_score=seo_score,
            accessibility_score=a11y_score,
            best_practices_score=bp_score,
            lcp_ms=round(lcp_val, 1) if lcp_val is not None else None,
            cls=round(cls_val, 3) if cls_val is not None else None,
            tbt_ms=round(tbt_val, 1) if tbt_val is not None else None,
            fcp_ms=round(fcp_val, 1) if fcp_val is not None else None,
            speed_index_ms=round(si_val, 1) if si_val is not None else None,
            raw_report_path=str(report_file),
        )

        logger.info(
            f"Lighthouse finished for #{business_id}: Perf={perf_score}, SEO={seo_score}, A11y={a11y_score}"
        )
        return result

    except Exception as e:
        logger.error(f"Lighthouse execution error for #{business_id}: {e}")
        return None
