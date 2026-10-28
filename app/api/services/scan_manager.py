import asyncio
import logging
from app.api.services.executor_contract import ScanExecutor
from datetime import datetime
from typing import Any, Dict, Optional

from app.database.connection import db_session
from app.database.models import PipelineRun
from app.database.repositories import PipelineRunRepository
from app.pipeline.runner import PipelineRunner
from app.config.settings import get_settings

logger = logging.getLogger("leadengine.api.scan_manager")


class LocalScanExecutor(ScanExecutor):
    """Local single-worker asynchronous scan executor with max 1 concurrent heavy scan."""

    def __init__(self, max_concurrent: int = 1):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_tasks: Dict[int, asyncio.Task] = {}

    async def _execute_scan(
        self,
        run_id: int,
        market: str,
        vertical: str,
        target: int,
        settings: Optional[Dict[str, Any]],
        is_resume: bool = False,
    ):
        async with self._semaphore:
            logger.info(f"Starting execution of scan #{run_id} ({market} - {vertical})")
            runner = PipelineRunner()
            try:
                def execute():
                    if settings and settings.get("fixture"):
                        from app.pipeline.fixtures import run_fixture
                        return run_fixture(run_id)
                    return asyncio.run(runner.run(market=market,vertical=vertical,target=target,run_id=run_id,run_configuration=settings))
                await asyncio.to_thread(execute)
            except asyncio.CancelledError:
                logger.info(f"Scan #{run_id} task was cancelled.")
            except Exception as e:
                logger.exception(f"Scan #{run_id} failed with error: {e}")
            finally:
                self._active_tasks.pop(run_id, None)
                with db_session() as conn:
                    row = conn.execute("SELECT campaign_id FROM pipeline_runs WHERE id=?", (run_id,)).fetchone()
                    if row and row[0]:
                        from app.api.routes.campaigns import campaign_detail
                        campaign_detail(conn, row[0], persist=True)

    async def start(
        self,
        run_id: int,
        market: str,
        vertical: str,
        target: int,
        settings: Optional[Dict[str, Any]] = None,
    ) -> None:
        task = asyncio.create_task(
            self._execute_scan(
                run_id=run_id,
                market=market,
                vertical=vertical,
                target=target,
                settings=settings,
                is_resume=False,
            )
        )
        self._active_tasks[run_id] = task

    async def cancel(self, run_id: int) -> bool:
        with db_session() as conn:
            run_repo = PipelineRunRepository(conn)
            cancelled = run_repo.cancel_run(run_id)
            conn.commit()

        task = self._active_tasks.get(run_id)
        if task and not task.done():
            # Worker thread reads persisted cancellation between bounded units.
            return True
        return cancelled

    async def resume(self, run_id: int) -> bool:
        if run_id in self._active_tasks and not self._active_tasks[run_id].done():
            return False
        with db_session() as conn:
            run_repo = PipelineRunRepository(conn)
            run = run_repo.get_by_id(run_id)
            if not run:
                return False
            run.status = "QUEUED"
            conn.execute("UPDATE pipeline_runs SET cancellation_requested=0 WHERE id=?", (run_id,))
            run_repo.update(run)
            conn.commit()

        settings = run.run_configuration or {}
        task = asyncio.create_task(
            self._execute_scan(
                run_id=run.id,
                market=run.market,
                vertical=run.vertical,
                target=run.target,
                settings=settings,
                is_resume=True,
            )
        )
        self._active_tasks[run.id] = task
        return True

    def status(self, run_id: int) -> Optional[str]:
        task = self._active_tasks.get(run_id)
        if task and not task.done():
            return "RUNNING"
        with db_session() as conn:
            run = PipelineRunRepository(conn).get_by_id(run_id)
            return run.status if run else None


class ScanManager:
    """Manages high-level scan orchestration, queueing, and lifecycle."""

    def __init__(self, executor: Optional[ScanExecutor] = None):
        if executor:
            self.executor = executor
        elif get_settings().scan_executor == "gcp":
            from app.api.services.cloud_executor import CloudRunScanExecutor
            self.executor = CloudRunScanExecutor()
        else:
            self.executor = LocalScanExecutor(max_concurrent=1)

    async def create_and_start_scan(
        self,
        market: str,
        vertical: str,
        target: int = 50,
        settings: Optional[Dict[str, Any]] = None,
    ) -> int:
        with db_session() as conn:
            run_repo = PipelineRunRepository(conn)
            new_run = PipelineRun(
                market=market,
                vertical=vertical,
                target=target,
                status="QUEUED",
                started_at=datetime.now().isoformat(),
                run_configuration=settings,
            )
            run_id = run_repo.create(new_run)
            conn.commit()

        await self.executor.start(
            run_id=run_id,
            market=market,
            vertical=vertical,
            target=target,
            settings=settings,
        )
        return run_id

    async def cancel_scan(self, run_id: int) -> bool:
        return await self.executor.cancel(run_id)

    async def resume_scan(self, run_id: int) -> bool:
        return await self.executor.resume(run_id)

    def get_status(self, run_id: int) -> Optional[str]:
        return self.executor.status(run_id)


# Global singleton instance
scan_manager = ScanManager()
