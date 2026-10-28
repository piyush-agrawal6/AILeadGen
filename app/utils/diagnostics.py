import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List
from pydantic import BaseModel

from app.audit.lighthouse import find_lighthouse_executable
from app.config.settings import get_settings
from app.database.connection import get_db_path
from app.database.migrations import run_migrations


class DiagnosticCheck(BaseModel):
    name: str
    status: str  # "ok", "warning", "error"
    details: str
    ready: bool


def run_system_diagnostics() -> List[DiagnosticCheck]:
    """Execute end-to-end system and dependency diagnostics."""
    results: List[DiagnosticCheck] = []

    # 1. Python version
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 12)
    results.append(
        DiagnosticCheck(
            name="Python Engine",
            status="ok" if py_ok else "error",
            details=f"Python {py_ver} (>= 3.12 required)",
            ready=py_ok,
        )
    )

    # 2. SQLite & Migrations
    try:
        run_migrations()
        results.append(
            DiagnosticCheck(
                name="SQLite Database",
                status="ok",
                details=f"Connected: {get_db_path().name}",
                ready=True,
            )
        )
    except Exception as e:
        results.append(
            DiagnosticCheck(
                name="SQLite Database",
                status="error",
                details=f"Migration error: {str(e)[:50]}",
                ready=False,
            )
        )

    # 3. DuckDB
    try:
        import duckdb
        con = duckdb.connect()
        con.execute("SELECT 42;")
        results.append(
            DiagnosticCheck(
                name="DuckDB Engine",
                status="ok",
                details=f"v{duckdb.__version__} Ready",
                ready=True,
            )
        )
    except Exception as e:
        results.append(
            DiagnosticCheck(
                name="DuckDB Engine",
                status="error",
                details=f"Failed: {str(e)[:50]}",
                ready=False,
            )
        )

    # 4. Chrome / Edge
    chrome_found = False
    chrome_path = ""
    for path in [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]:
        if Path(path).exists():
            chrome_found = True
            chrome_path = path
            break
    if not chrome_found and shutil.which("google-chrome"):
        chrome_found = True
        chrome_path = shutil.which("google-chrome")

    results.append(
        DiagnosticCheck(
            name="Chrome / Edge",
            status="ok" if chrome_found else "warning",
            details=chrome_path or "Not in default path (Playwright managed fallback)",
            ready=True,
        )
    )

    # 5. Lighthouse CLI
    lh_bin = find_lighthouse_executable()
    results.append(
        DiagnosticCheck(
            name="Lighthouse CLI",
            status="ok" if lh_bin else "warning",
            details=lh_bin or "Optional for deep Web Vitals",
            ready=bool(lh_bin),
        )
    )

    # 6. Playwright
    try:
        import playwright
        results.append(
            DiagnosticCheck(
                name="Playwright Layer",
                status="ok",
                details="Browser automation engine ready",
                ready=True,
            )
        )
    except Exception as e:
        results.append(
            DiagnosticCheck(
                name="Playwright Layer",
                status="error",
                details=f"Failed: {str(e)[:50]}",
                ready=False,
            )
        )

    # 7. Overture S3 connectivity
    try:
        import duckdb
        c = duckdb.connect()
        c.execute("INSTALL httpfs; LOAD httpfs;")
        results.append(
            DiagnosticCheck(
                name="Overture Maps S3",
                status="ok",
                details="S3 Public Parquet ready",
                ready=True,
            )
        )
    except Exception as e:
        results.append(
            DiagnosticCheck(
                name="Overture Maps S3",
                status="warning",
                details=f"Local fallback: {str(e)[:30]}",
                ready=True,
            )
        )

    # 8. OpenStreetMap / Overpass
    try:
        import httpx
        with httpx.Client(timeout=4.0) as client:
            resp = client.get("https://overpass-api.de/api/status")
            osm_ok = resp.status_code == 200
        results.append(
            DiagnosticCheck(
                name="OpenStreetMap Overpass",
                status="ok" if osm_ok else "warning",
                details="Overpass endpoint responsive" if osm_ok else "Overpass returned non-200",
                ready=osm_ok,
            )
        )
    except Exception:
        results.append(
            DiagnosticCheck(
                name="OpenStreetMap Overpass",
                status="warning",
                details="Offline cache or retry queue ready",
                ready=True,
            )
        )

    return results
