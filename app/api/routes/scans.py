import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse

from app.api.dependencies import get_db
from app.api.schemas.scans import (
    PipelineEventSchema,
    PipelineRunDetail,
    ScanCreateRequest,
    ScanCreateResponse,
)
from app.api.services.event_stream import stream_scan_events
from app.api.services.scan_manager import scan_manager
from app.database.repositories import PipelineRunEventRepository, PipelineRunRepository

router = APIRouter(prefix="/scans", tags=["Scans"])


@router.get("", response_model=List[PipelineRunDetail])
def list_scans(
    status_filter: Optional[str] = Query(None, alias="status"),
    vertical_filter: Optional[str] = Query(None, alias="vertical"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    conn: sqlite3.Connection = Depends(get_db),
):
    """List historical and active pipeline runs."""
    repo = PipelineRunRepository(conn)
    runs, _ = repo.list_runs(status=status_filter, vertical=vertical_filter, page=page, page_size=page_size)

    details = []
    for r in runs:
        duration = None
        if r.started_at and r.finished_at:
            try:
                t0 = datetime.fromisoformat(r.started_at)
                t1 = datetime.fromisoformat(r.finished_at)
                duration = round((t1 - t0).total_seconds(), 1)
            except Exception:
                duration = None

        details.append(
            PipelineRunDetail(
                id=r.id,
                market=r.market,
                vertical=r.vertical,
                target=r.target,
                started_at=r.started_at,
                finished_at=r.finished_at,
                status=r.status,
                raw_found=r.raw_found,
                deduped=r.deduped,
                filtered=r.filtered,
                websites_processed=r.websites_processed,
                qualified=r.qualified,
                exported=r.exported,
                output_file=r.output_file,
                error_message=r.error_message,
                cancelled_at=r.cancelled_at,
                run_configuration=r.run_configuration,
                duration_seconds=duration,
            )
        )
    return details


@router.post("", response_model=ScanCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_scan(req: ScanCreateRequest):
    """Queue and initiate a new LeadEngine prospecting scan."""
    settings_dict = req.settings.model_dump() if req.settings else {}
    settings_dict["target"] = req.target

    run_id = await scan_manager.create_and_start_scan(
        market=req.market.strip(),
        vertical=req.vertical.strip().lower(),
        target=req.target,
        settings=settings_dict,
    )

    return ScanCreateResponse(
        run_id=run_id,
        status="QUEUED",
        message=f"Scan #{run_id} queued successfully for {req.market} ({req.vertical})",
    )


@router.get("/{run_id}", response_model=PipelineRunDetail)
def get_scan(run_id: int, conn: sqlite3.Connection = Depends(get_db)):
    """Fetch live or historical status of a specific pipeline run."""
    repo = PipelineRunRepository(conn)
    r = repo.get_by_id(run_id)
    if not r:
        raise HTTPException(status_code=404, detail=f"Scan #{run_id} not found.")

    duration = None
    if r.started_at and r.finished_at:
        try:
            t0 = datetime.fromisoformat(r.started_at)
            t1 = datetime.fromisoformat(r.finished_at)
            duration = round((t1 - t0).total_seconds(), 1)
        except Exception:
            duration = None

    return PipelineRunDetail(
        id=r.id,
        market=r.market,
        vertical=r.vertical,
        target=r.target,
        started_at=r.started_at,
        finished_at=r.finished_at,
        status=r.status,
        raw_found=r.raw_found,
        deduped=r.deduped,
        filtered=r.filtered,
        websites_processed=r.websites_processed,
        qualified=r.qualified,
        exported=r.exported,
        output_file=r.output_file,
        error_message=r.error_message,
        cancelled_at=r.cancelled_at,
        run_configuration=r.run_configuration,
        duration_seconds=duration,
    )


@router.post("/{run_id}/cancel")
async def cancel_scan(run_id: int):
    """Request graceful cancellation of a running or queued scan."""
    success = await scan_manager.cancel_scan(run_id)
    if not success:
        raise HTTPException(status_code=400, detail=f"Could not cancel scan #{run_id}. It may already be finished.")
    return {"success": True, "message": f"Scan #{run_id} cancellation requested."}


@router.post("/{run_id}/resume")
async def resume_scan(run_id: int,conn=Depends(get_db)):
    """Resume an interrupted, cancelled, or failed scan."""
    from app.database.phase36_schema import phase36_ready
    if getattr(conn,'backend',None)=='postgres':conn.execute('SELECT pg_advisory_xact_lock(691944307)')
    if phase36_ready(conn) and conn.execute("SELECT 1 FROM deletion_batches d WHERE (d.entity_type='scan' AND d.entity_id=?) OR (d.entity_type='campaign' AND d.entity_id=(SELECT campaign_id FROM pipeline_runs WHERE id=?))",(str(run_id),run_id)).fetchone():raise HTTPException(409,'Finish the pending deletion before resuming this scan.')
    if phase36_ready(conn) and conn.execute('SELECT 1 FROM deletion_targets d JOIN businesses b ON b.id=d.business_id WHERE b.run_id=?',(run_id,)).fetchone():raise HTTPException(409,'Finish the pending deletion before resuming this scan.')
    success = await scan_manager.resume_scan(run_id)
    if not success:
        raise HTTPException(status_code=400, detail=f"Could not resume scan #{run_id}.")
    return {"success": True, "message": f"Scan #{run_id} resumption queued."}


@router.get("/{run_id}/events", response_model=List[PipelineEventSchema])
def get_scan_events(
    run_id: int,
    after_id: Optional[int] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Retrieve event log history for a pipeline run."""
    event_repo = PipelineRunEventRepository(conn)
    events = event_repo.list_by_run(run_id=run_id, after_id=after_id, limit=limit)
    return [
        PipelineEventSchema(
            id=e.id,
            run_id=e.run_id,
            timestamp=e.timestamp,
            stage=e.stage,
            event_type=e.event_type,
            message=e.message,
            completed=e.completed,
            total=e.total,
            metadata_json=e.metadata_json,
        )
        for e in events
    ]


@router.get("/{run_id}/events/stream")
async def stream_events(run_id: int):
    """Subscribe to real-time Server-Sent Events (SSE) for a pipeline run."""
    return EventSourceResponse(stream_scan_events(run_id))


@router.get("/{run_id}/export/xlsx")
def download_xlsx(run_id: int, conn: sqlite3.Connection = Depends(get_db)):
    """Safely download the Excel (.xlsx) export artifact for a scan."""
    from app.storage import download_artifact
    artifact = download_artifact(conn, run_id=run_id, kind="xlsx")
    if artifact is not None:
        return artifact
    repo = PipelineRunRepository(conn)
    run = repo.get_by_id(run_id)
    if not run or not run.output_file:
        raise HTTPException(status_code=404, detail="No export file registered for this scan.")

    path = Path(run.output_file).resolve()
    # Security check: must reside inside output/ directory
    allowed_dir = Path("output").resolve()
    if not path.is_relative_to(allowed_dir) or not path.is_file():
        raise HTTPException(status_code=404, detail="Excel artifact file not found on server.")

    return FileResponse(
        path=path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=path.name,
    )


@router.get("/{run_id}/export/csv")
def download_csv(run_id: int, conn: sqlite3.Connection = Depends(get_db)):
    """Safely download the CSV (.csv) export artifact for a scan."""
    from app.storage import download_artifact
    artifact = download_artifact(conn, run_id=run_id, kind="csv")
    if artifact is not None:
        return artifact
    repo = PipelineRunRepository(conn)
    run = repo.get_by_id(run_id)
    if not run or not run.output_file:
        raise HTTPException(status_code=404, detail="No export file registered for this scan.")

    # Derive csv path from xlsx path
    xlsx_path = Path(run.output_file).resolve()
    csv_path = xlsx_path.with_suffix(".csv")

    allowed_dir = Path("output").resolve()
    if not csv_path.is_relative_to(allowed_dir) or not csv_path.is_file():
        raise HTTPException(status_code=404, detail="CSV artifact file not found on server.")

    return FileResponse(
        path=csv_path,
        media_type="text/csv",
        filename=csv_path.name,
    )
