import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.config.settings import get_settings
from app.database.connection import db_session
from app.database.models import PipelineRun,PipelineRunEvent,ProcessingStatus
from app.database.repositories import BusinessRepository,PipelineRunEventRepository,PipelineRunRepository
from app.discovery.resolver import DiscoveryCoordinator
from app.enrichment.crawler import WebsiteCrawler
from app.pipeline.progress import PipelineDisplay
from app.database.prospects import ProspectRepository

logger = logging.getLogger("leadengine.pipeline.runner")


class PipelineRunner:
    def __init__(self, db_path: Optional[Path] = None, output_dir: Optional[Path] = None, *, discovery_coordinator=None, execution_limits=None):
        self.settings = get_settings().model_copy(deep=True)
        self.execution_limits=execution_limits or {}
        self.db_path = db_path
        self.output_dir = output_dir or Path("output")
        self.discovery_coord = discovery_coordinator if discovery_coordinator is not None else DiscoveryCoordinator()
        self.crawler = WebsiteCrawler(
            max_pages=min(3,self.settings.crawl_max_pages),
            page_timeout=self.settings.crawler.page_timeout_seconds,
            max_duration=self.settings.crawler.max_site_duration_seconds,
            max_response_bytes=min(500_000,self.settings.crawler.max_response_bytes),
        )

    async def run(
        self,
        market: str,
        vertical: str,
        target: int = 250,
        include_chains: bool = False,
        run_id: Optional[int] = None,
        enable_lighthouse: bool = False,
        run_configuration: Optional[Dict[str, Any]] = None,
    ) -> PipelineRun:
        """Execute the end-to-end LeadEngine discovery and qualification pipeline."""
        from app.platform.context import organization
        workspace=organization()
        from app.prospecting.policy import configuration as prospecting_configuration
        run_configuration=prospecting_configuration(run_configuration)
        start_time = time.time()
        output_dir = self.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        # Apply settings overrides from run_configuration if provided
        if run_configuration:
            self.discovery_coord.raw_limit = min(self.settings.max_raw_businesses,run_configuration.get("raw_budget") or run_configuration.get("max_candidates") or 300)
            self.discovery_coord.phase3_scale = "quality" in run_configuration
            if "exclude_chains" in run_configuration:
                include_chains = not bool(run_configuration["exclude_chains"])
            if "lighthouse_enabled" in run_configuration:
                enable_lighthouse = bool(run_configuration["lighthouse_enabled"])
            if "target" in run_configuration:
                target = int(run_configuration["target"])

            crawl_opts = {
                "max_pages": run_configuration.get("crawler_max_pages") or run_configuration.get("max_pages"),
                "page_timeout": run_configuration.get("page_timeout") or run_configuration.get("page_timeout_seconds"),
                "max_duration": run_configuration.get("site_timeout") or run_configuration.get("site_timeout_seconds"),
                "max_response_bytes": run_configuration.get("max_response_bytes"),
            }
            if any(crawl_opts.values()):
                self.crawler = WebsiteCrawler(
                    max_pages=min(3,crawl_opts["max_pages"] or self.settings.crawl_max_pages),
                    page_timeout=crawl_opts["page_timeout"] or self.settings.crawler.page_timeout_seconds,
                    max_duration=crawl_opts["max_duration"] or self.settings.crawler.max_site_duration_seconds,
                    max_response_bytes=crawl_opts["max_response_bytes"] or self.settings.crawler.max_response_bytes,
                )

        with db_session(self.db_path) as conn:
            from app.database.migrations import run_migrations
            if self.settings.app_env == "production":
                from app.database.migrations import verify_schema
                verify_schema(conn)
            else:
                run_migrations(conn)
            if (run_configuration or {}).get('locations'):
                from app.config.locations import seed_selected
                seed_selected(conn,run_configuration['locations'],[vertical])
                conn.commit()
            from app.api.organization import workspace_settings
            shared=workspace_settings(conn,workspace)
            frozen=(run_configuration or {}).get('crawler')
            if shared or frozen:
                configuration = shared or {}
                crawler = frozen or configuration.get("crawler", {})
                self.settings.crawl_max_pages = min(3,crawler.get("max_pages",3))
                self.settings.crawl_concurrency = min(4,crawler.get("crawl_concurrency",2))
                self.settings.http_concurrency = min(10,crawler.get("http_concurrency",5))
                self.crawler = WebsiteCrawler(max_pages=self.settings.crawl_max_pages,page_timeout=min(8,crawler.get("page_timeout_seconds",6)),max_duration=min(22,crawler.get("max_site_duration_seconds",20)),max_response_bytes=min(500_000,crawler.get("max_response_bytes",500_000)))
            for key in ('crawl_concurrency','http_concurrency'):
                if key in self.execution_limits:setattr(self.settings,key,min(getattr(self.settings,key),max(1,int(self.execution_limits[key]))))
            run_repo = PipelineRunRepository(conn)
            event_repo = PipelineRunEventRepository(conn)
            biz_repo = BusinessRepository(conn)

            # Setup or resume PipelineRun
            if run_id:
                pipeline_run = run_repo.get_by_id(run_id,organization=workspace)
                if not pipeline_run:
                    raise ValueError(f"Pipeline run #{run_id} not found to resume.")
                pipeline_run.status = "RUNNING"
                pipeline_run.error_message = None
                pipeline_run.cancelled_at = None
                run_repo.update(pipeline_run)
                conn.commit()
                PipelineDisplay.print_stage_start(1, 9, f"Resuming Pipeline Run #{run_id}...")
            else:
                pipeline_run = PipelineRun(
                    market=market,
                    vertical=vertical,
                    target=target,
                    status="RUNNING",
                    started_at=datetime.now().isoformat(),
                    run_configuration=run_configuration,
                )
                pipeline_run.id = run_repo.create(pipeline_run,organization=workspace)
                conn.commit()

            def emit_event(
                stage: str,
                event_type: str,
                message: str,
                completed: int = 0,
                total: int = 0,
                metadata: Optional[Dict[str, Any]] = None,
            ):
                evt = PipelineRunEvent(
                    run_id=pipeline_run.id,
                    timestamp=datetime.now().isoformat(),
                    stage=stage,
                    event_type=event_type,
                    message=message,
                    completed=completed,
                    total=total,
                    metadata_json=json.dumps(metadata) if metadata else None,
                )
                try:
                    event_repo.insert(evt)
                    conn.commit()
                except Exception as ex:
                    logger.warning(f"Failed to record pipeline event: {ex}")

            from app.database.foundation_schema import ready as foundation_ready
            attempt_id=None
            if foundation_ready(conn):
                import uuid
                from app.workflows.health import record as record_health
                record_health('scan','RUNNING')
                attempt_id=str(uuid.uuid4())
                conn.execute("INSERT INTO worker_attempts(id,run_id,started_at,status) VALUES(?,?,?,'RUNNING')",(attempt_id,pipeline_run.id,datetime.now().isoformat()))
                conn.commit()

            def runtime_limit():
                return min(self.settings.max_scan_runtime_minutes * 60,(run_configuration or {}).get('max_runtime_seconds') or self.settings.max_scan_runtime_minutes * 60)

            def check_cancellation(*,finalizing=False):
                # A short bounded grace writes already-computed results/exports;
                # it never authorizes another discovery, crawl or screenshot.
                allowance=90 if finalizing and (run_configuration or {}).get('qualification_flow_version')==1 else 0
                if time.time() - start_time > runtime_limit()+allowance:
                    raise TimeoutError("Scan runtime safety limit reached")
                cur = conn.execute("SELECT status, cancellation_requested FROM pipeline_runs WHERE id = ?", (pipeline_run.id,))
                row = cur.fetchone()
                if row and (row["status"] == "CANCELLED" or row["cancellation_requested"]):
                    raise asyncio.CancelledError(f"Pipeline run #{pipeline_run.id} cancelled by user.")
                campaign_row = conn.execute("SELECT c.cancellation_requested FROM scan_campaigns c JOIN pipeline_runs r ON r.campaign_id=c.id WHERE r.id=?", (pipeline_run.id,)).fetchone()
                if campaign_row:
                    if campaign_row[0]:
                        raise asyncio.CancelledError("Campaign cancellation requested")
                    # The bounded execution timer above restarts on an explicit
                    # resume. Campaign creation time is historical metadata;
                    # using it here makes every later checkpoint resume fail.

            try:
                emit_event(
                    stage="INITIALIZATION",
                    event_type="RUN_CREATED" if not run_id else "RUN_RESUMED",
                    message=f"Pipeline run #{pipeline_run.id} started for {market} ({vertical}) target {target}",
                    metadata={"market": market, "vertical": vertical, "target": target},
                )

                # Stage 1: Market Resolution
                check_cancellation()
                PipelineDisplay.print_stage_start(1, 9, f"Resolving market '{market}'...")
                emit_event(
                    stage="MARKET",
                    event_type="MARKET_RESOLVING",
                    message=f"Resolving market geographic coordinates for '{market}'...",
                )

                prior = conn.execute("SELECT * FROM businesses WHERE run_id=? ORDER BY id", (pipeline_run.id,)).fetchall()
                observed_ids={row['id'] for row in prior if row['prospect_id']}
                progressive=bool(getattr(self.discovery_coord,'supports_progressive',False))
                finished_discovery=conn.execute("SELECT 1 FROM pipeline_run_events WHERE run_id=? AND event_type='DISCOVERY_COMPLETE' LIMIT 1",(pipeline_run.id,)).fetchone()
                if progressive:
                    saved=[biz_repo._row_to_business(row) for row in prior]
                    self.discovery_coord.completed_sources={json.loads(row[0])['source'] for row in conn.execute("SELECT metadata_json FROM pipeline_run_events WHERE run_id=? AND event_type='SOURCE_BATCH_SAVED'",(pipeline_run.id,)).fetchall() if row[0] and json.loads(row[0]).get('source')} if not finished_discovery else set()
                    self.discovery_coord.existing_businesses=[business for business in saved if json.loads(business.source_tags or '{}').get('discovery_source') in self.discovery_coord.completed_sources]
                    def source_batch(source,values,error=None):
                        check_cancellation()
                        for business in values:
                            check_cancellation()
                            business.run_id=pipeline_run.id;business.processing_status='NORMALIZED'
                            tag=json.loads(business.source_tags or '{}');tag['discovery_source']=source;business.source_tags=json.dumps(tag)
                            identifier=business.external_overture_id if source=='OVERTURE' else business.external_osm_id
                            if identifier:
                                column='external_overture_id' if source=='OVERTURE' else 'external_osm_id'
                                old=conn.execute('SELECT id FROM businesses WHERE run_id=? AND '+column+'=?',(pipeline_run.id,identifier)).fetchone()
                                if old:business.id=old[0]
                            if not business.id:biz_repo.insert(business)
                            try:ProspectRepository(conn).observe(business,conn.execute('SELECT campaign_id FROM pipeline_runs WHERE id=?',(pipeline_run.id,)).fetchone()[0],organization=workspace)
                            except ValueError:
                                business.rejection_reason='CANONICAL_IDENTITY_REVIEW_REQUIRED';biz_repo.update(business)

                        pipeline_run.raw_found=conn.execute('SELECT COUNT(*) FROM businesses WHERE run_id=?',(pipeline_run.id,)).fetchone()[0]
                        run_repo.update(pipeline_run);conn.commit()
                        emit_event(stage='DISCOVERY',event_type='SOURCE_FAILED' if error else 'SOURCE_BATCH_SAVED',message=source+(' source unavailable; other sources continue.' if error else ' company results are available.'),completed=len(values),total=target,metadata={'source':source,'error_code':error,'time_to_first_result_seconds':round(time.time()-start_time,3) if values else None,'results_saved':len(values)})
                    self.discovery_coord.on_batch=source_batch
                    self.discovery_coord.check_cancel=check_cancellation
                if prior and (not progressive or finished_discovery):
                    from app.config.markets import resolve_market
                    market_res = getattr(self.discovery_coord, "resolve_market", resolve_market)(market)
                    vert_res = self.discovery_coord.vertical_mgr.resolve_vertical(vertical)
                    observations = [biz_repo._row_to_business(row) for row in prior]
                    candidates = [b for b in observations if not b.is_rejected]
                    rejected = [b for b in observations if b.is_rejected]
                else:
                    market_res, vert_res, candidates, rejected = self.discovery_coord.discover(
                        market_str=market, vertical_str=vertical, target_leads=target, include_chains=include_chains,
                    )
                PipelineDisplay.print_stage_success(
                    f"Market resolved: {market_res.city}, {market_res.state} {market_res.country} "
                    f"(lat: {market_res.center_lat:.3f}, lon: {market_res.center_lon:.3f})"
                )
                emit_event(
                    stage="MARKET",
                    event_type="MARKET_RESOLVED",
                    message=f"Market resolved: {market_res.city}, {market_res.state} {market_res.country}",
                    metadata={
                        "city": market_res.city,
                        "state": market_res.state,
                        "country": market_res.country,
                        "lat": market_res.center_lat,
                        "lon": market_res.center_lon,
                    },
                )

                # Stage 2 & 3: Discovery & Deduplication results
                check_cancellation()
                PipelineDisplay.print_stage_start(2, 9, "Discovering public businesses...")
                raw_total = len(candidates) + len(rejected)
                PipelineDisplay.print_stage_success(f"Discovered: {raw_total:,} raw listings")
                emit_event(
                    stage="DISCOVERY",
                    event_type="DISCOVERY_COMPLETE",
                    message=f"Discovered {raw_total:,} raw listings across data sources",
                    completed=raw_total,
                    total=raw_total,
                )

                PipelineDisplay.print_stage_start(3, 9, "Deduplicating & normalising...")
                deduped_total = len(candidates)
                PipelineDisplay.print_stage_success(f"{deduped_total:,} unique candidate businesses")
                emit_event(
                    stage="DEDUPLICATION",
                    event_type="DEDUPE_COMPLETE",
                    message=f"Identified {deduped_total:,} unique businesses after deduplication",
                    completed=deduped_total,
                    total=raw_total,
                )

                PipelineDisplay.print_stage_start(4, 9, "Filtering franchise chains & invalid entities...")
                PipelineDisplay.print_stage_success(f"{len(candidates):,} valid prospect candidates")
                emit_event(
                    stage="FILTERING",
                    event_type="FILTER_COMPLETE",
                    message=f"{len(candidates):,} candidates verified after quality & chain filtering ({len(rejected):,} rejected)",
                    completed=len(candidates),
                    total=raw_total,
                )

                # Persist discovered candidates and rejected entities with run_id
                campaign = conn.execute("SELECT campaign_id FROM pipeline_runs WHERE id=?", (pipeline_run.id,)).fetchone()[0]
                pipeline_run.raw_found = raw_total
                pipeline_run.deduped = deduped_total
                pipeline_run.filtered = len(candidates)
                run_repo.update(pipeline_run)
                conn.commit()
                run_organization=conn.execute("SELECT organization_id FROM pipeline_runs WHERE id=?", (pipeline_run.id,)).fetchone()[0]
                for index,b in enumerate(candidates):
                    check_cancellation()
                    b.run_id = pipeline_run.id
                    if not b.id:
                        biz_repo.insert(b)
                    if (run_configuration or {}).get('qualification_mode')!='CONTACTABLE_ONLY' and b.id not in observed_ids:
                        try:
                            ProspectRepository(conn).observe(b, campaign, (run_configuration or {}).get("created_by"), organization=run_organization)
                        except ValueError as exc:
                            if str(exc)!='Conflicting canonical identity evidence':raise
                            b.processing_status=ProcessingStatus.REJECTED.value
                            b.is_rejected=True;b.rejection_reason='CANONICAL_IDENTITY_REVIEW_REQUIRED'
                            biz_repo.update(b)
                            emit_event(stage="IDENTITY",event_type="IDENTITY_REVIEW_REQUIRED",message="Conflicting permanent identity evidence requires operator review.",metadata={"business_id":b.id})
                            rejected.append(b)

                    if (index+1)%20==0:
                        emit_event(stage="IDENTITY",event_type="IDENTITY_PROGRESS",message=f"Saved {index+1} of {len(candidates)} canonical observations",completed=index+1,total=len(candidates))
                candidates=[b for b in candidates if b.rejection_reason!='CANONICAL_IDENTITY_REVIEW_REQUIRED']
                for r in rejected:
                    r.run_id = pipeline_run.id
                    if not r.id:
                        biz_repo.insert(r)
                    else:biz_repo.update(r)

                pipeline_run.raw_found = raw_total
                pipeline_run.deduped = deduped_total
                pipeline_run.filtered = len(candidates)
                run_repo.update(pipeline_run)
                conn.commit()

                from app.prospecting.intake import process,exports
                results=await process(conn,candidates,campaign,run_configuration,self.crawler,check_cancellation,emit_event)
                check_cancellation()
                qualified=[biz_repo._row_to_business(row) for row in conn.execute("SELECT * FROM businesses WHERE run_id=? AND processing_status='QUALIFIED' AND is_duplicate=0 AND is_rejected=0 ORDER BY id",(pipeline_run.id,)).fetchall()]
                pipeline_run.qualified=len(qualified)
                pipeline_run.websites_processed=results['company_information']
                pipeline_run.output_file,pipeline_run.exported=exports(conn,pipeline_run,qualified,output_dir)
                pipeline_run.status='COMPLETED';pipeline_run.finished_at=datetime.now().isoformat()
                provider_errors=getattr(self.discovery_coord,'provider_errors',{})
                if provider_errors:emit_event(stage='DISCOVERY',event_type='SOURCE_PARTIAL_FAILURE',message='Some discovery sources were unavailable. Results from successful sources were retained.',metadata={'sources':provider_errors})
                pipeline_run.error_message=None if len(qualified)>=target else f'TARGET_NOT_REACHED: {len(qualified)}/{target}; bounded discovery pool exhausted.'
                run_repo.update(pipeline_run)
                from app.automation.service import reconcile
                reconcile(conn);conn.commit()
                emit_event(stage='COMPLETION',event_type='RUN_COMPLETED',message=f"Saved {len(qualified)} qualified companies. No website assessments were run.",completed=len(qualified),total=target,metadata=results)
                return pipeline_run

            except asyncio.CancelledError:
                conn.rollback()
                pipeline_run.status = "CANCELLED"
                pipeline_run.cancelled_at = datetime.now().isoformat()
                pipeline_run.finished_at = datetime.now().isoformat()
                run_repo.update(pipeline_run)
                emit_event(
                    stage="CANCELLED",
                    event_type="RUN_CANCELLED",
                    message=f"Pipeline run #{pipeline_run.id} was cancelled by user.",
                )
                conn.commit()
                logger.info(f"Pipeline run #{pipeline_run.id} cancelled.")
                return pipeline_run

            except Exception as e:
                conn.rollback()
                production = self.settings.app_env == "production"
                if production:
                    logger.error("Pipeline run failed: run=%s type=%s",pipeline_run.id,type(e).__name__)
                else:
                    logger.exception(f"Pipeline run #{pipeline_run.id} encountered an error: {e}")
                pipeline_run.status = "FAILED"
                failure_class = "quota/resource" if isinstance(e,TimeoutError) else "permanent" if isinstance(e,ValueError) else "transient"
                pipeline_run.error_message = "Scan could not complete. Review worker health and resume from the checkpoint." if production else str(e)
                pipeline_run.finished_at = datetime.now().isoformat()
                run_repo.update(pipeline_run)
                conn.execute("UPDATE pipeline_runs SET failure_class=? WHERE id=?",(failure_class,pipeline_run.id))
                emit_event(
                    stage="FAILURE",
                    event_type="RUN_FAILED",
                    message=f"Pipeline run failed: {pipeline_run.error_message[:250]}",
                    metadata={"failure_class":failure_class},
                )
                conn.commit()
                raise
            finally:
                if attempt_id:
                    try:
                        conn.execute('UPDATE worker_attempts SET finished_at=?,runtime_seconds=?,status=? WHERE id=?',(datetime.now().isoformat(),round(time.time()-start_time,3),pipeline_run.status,attempt_id))
                        conn.commit()
                        record_health('scan','READY' if pipeline_run.status=='COMPLETED' else 'FAILED',None if pipeline_run.status=='COMPLETED' else pipeline_run.status)
                    except Exception:
                        conn.rollback()
                        logger.warning('Worker attempt metrics could not be finalized: run=%s',pipeline_run.id)
