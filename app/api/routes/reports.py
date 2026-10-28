import sqlite3
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.dependencies import get_db
from app.database.repositories import PipelineRunRepository

router = APIRouter(prefix="/reports", tags=["Reports"])


class ReportArtifactItem(BaseModel):
    run_id: int
    market: str
    vertical: str
    target: int
    qualified: int
    exported: int
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    status: str
    excel_url: Optional[str] = None
    csv_url: Optional[str] = None
    has_excel: bool = False
    has_csv: bool = False


@router.get("", response_model=List[ReportArtifactItem])
def list_reports(conn: sqlite3.Connection = Depends(get_db)):
    """List completed prospecting runs with export artifacts."""
    run_repo = PipelineRunRepository(conn)
    runs, _ = run_repo.list_runs(page=1, page_size=100)

    results = []
    for r in runs:
        has_xlsx = False
        has_csv = False
        xlsx_url = None
        csv_url = None
        objects = {row[0] for row in conn.execute("SELECT kind FROM artifact_objects WHERE run_id=?", (r.id,)).fetchall()}
        if "xlsx" in objects:
            has_xlsx = True
            xlsx_url = f"/api/scans/{r.id}/export/xlsx"
        if "csv" in objects:
            has_csv = True
            csv_url = f"/api/scans/{r.id}/export/csv"

        if r.output_file:
            p = Path(r.output_file)
            if p.exists():
                has_xlsx = True
                xlsx_url = f"/api/scans/{r.id}/export/xlsx"
            csv_p = p.with_suffix(".csv")
            if csv_p.exists():
                has_csv = True
                csv_url = f"/api/scans/{r.id}/export/csv"

        results.append(
            ReportArtifactItem(
                run_id=r.id,
                market=r.market,
                vertical=r.vertical,
                target=r.target,
                qualified=r.qualified,
                exported=r.exported,
                started_at=r.started_at,
                finished_at=r.finished_at,
                status=r.status,
                excel_url=xlsx_url,
                csv_url=csv_url,
                has_excel=has_xlsx,
                has_csv=has_csv,
            )
        )

    return results
