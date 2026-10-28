import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.audit.lighthouse import run_lighthouse_audit
from app.audit.quick import perform_quick_audit
from app.audit.vertical.hospitality import audit_hospitality
from app.audit.vertical.real_estate import audit_real_estate
from app.audit.vertical.restaurant import audit_restaurant
from app.config.settings import get_settings
from app.database.connection import db_session
from app.database.models import (
    Business,
    Contact,
    Finding,
    LeadScore,
    LighthouseResult,
    PipelineRun,
    PipelineRunEvent,
    ProcessingStatus,
    WebsiteProfile,
)
from app.database.repositories import (
    BusinessRepository,
    ContactRepository,
    FindingRepository,
    LeadScoreRepository,
    LighthouseRepository,
    PipelineRunEventRepository,
    PipelineRunRepository,
    WebsiteProfileRepository,
)
from app.discovery.resolver import DiscoveryCoordinator
from app.enrichment.contacts import ExtractedContacts
from app.enrichment.crawler import CrawlResult, WebsiteCrawler
from app.enrichment.dns import check_email_dns
from app.enrichment.http_probe import ProbeResult, probe_website
from app.exports.csv_export import export_leads_to_csv
from app.exports.excel_export import export_leads_to_excel
from app.pipeline.progress import PipelineDisplay
from app.scoring.scorer import calculate_lead_score
from app.database.prospects import ProspectRepository
from app.scoring.opportunities import analyze_opportunities, store_opportunities, classify_scale
from app.config.presets import quality_modes
from app.storage import publish_artifact
from app.exports.phase3 import attach_workflow
from app.database.phase36_schema import phase36_ready
from app.enrichment.social_intelligence import enrich_social, store_social, presence_summary
from app.scoring.commercial import classify_scale_v2, footprint_counts, commercial_fit, store_intelligence

logger = logging.getLogger("leadengine.pipeline.runner")


class PipelineRunner:
    def __init__(self, db_path: Optional[Path] = None, output_dir: Optional[Path] = None):
        self.settings = get_settings().model_copy(deep=True)
        self.db_path = db_path
        self.output_dir = output_dir or Path("output")
        self.discovery_coord = DiscoveryCoordinator()
        self.crawler = WebsiteCrawler(
            max_pages=self.settings.crawl_max_pages,
            page_timeout=self.settings.crawler.page_timeout_seconds,
            max_duration=self.settings.crawler.max_site_duration_seconds,
            max_response_bytes=self.settings.crawler.max_response_bytes,
        )

    async def run(
        self,
        market: str,
        vertical: str,
        target: int = 250,
        include_chains: bool = False,
        run_id: Optional[int] = None,
        enable_lighthouse: bool = True,
        run_configuration: Optional[Dict[str, Any]] = None,
    ) -> PipelineRun:
        """Execute the end-to-end LeadEngine discovery and qualification pipeline."""
        start_time = time.time()
        output_dir = self.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        # Apply settings overrides from run_configuration if provided
        if run_configuration:
            self.discovery_coord.raw_limit = run_configuration.get("raw_budget")
            self.discovery_coord.phase3_scale = "quality" in run_configuration
            if "SEO" in run_configuration.get("opportunities", []):
                self.crawler.max_pages = self.settings.seo_crawl_max_pages
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
                    max_pages=crawl_opts["max_pages"] or self.settings.crawl_max_pages,
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
            shared = conn.execute("SELECT configuration_json FROM shared_settings WHERE id=1").fetchone()
            if shared:
                configuration = json.loads(shared[0])
                crawler = configuration.get("crawler", {})
                auditing = configuration.get("auditing", {})
                self.settings.crawl_max_pages = min(30,crawler.get("max_pages",8))
                self.settings.crawl_concurrency = min(20,crawler.get("crawl_concurrency",4))
                self.settings.http_concurrency = min(100,crawler.get("http_concurrency",15))
                self.settings.audit.lighthouse_enabled = auditing.get("lighthouse_enabled",True)
                self.crawler = WebsiteCrawler(max_pages=self.settings.seo_crawl_max_pages if "SEO" in (run_configuration or {}).get("opportunities",[]) else (run_configuration or {}).get("max_pages",self.settings.crawl_max_pages),page_timeout=crawler.get("page_timeout_seconds",12),max_duration=crawler.get("max_site_duration_seconds",45),max_response_bytes=min(5_242_880,crawler.get("max_response_bytes",3_000_000)))
            run_repo = PipelineRunRepository(conn)
            event_repo = PipelineRunEventRepository(conn)
            biz_repo = BusinessRepository(conn)
            profile_repo = WebsiteProfileRepository(conn)
            contact_repo = ContactRepository(conn)
            lh_repo = LighthouseRepository(conn)
            finding_repo = FindingRepository(conn)
            score_repo = LeadScoreRepository(conn)

            # Setup or resume PipelineRun
            if run_id:
                pipeline_run = run_repo.get_by_id(run_id)
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
                pipeline_run.id = run_repo.create(pipeline_run)
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

            def check_cancellation():
                if time.time() - start_time > self.settings.max_scan_runtime_minutes * 60:
                    raise TimeoutError("Scan runtime safety limit reached")
                cur = conn.execute("SELECT status, cancellation_requested FROM pipeline_runs WHERE id = ?", (pipeline_run.id,))
                row = cur.fetchone()
                if row and (row["status"] == "CANCELLED" or row["cancellation_requested"]):
                    raise asyncio.CancelledError(f"Pipeline run #{pipeline_run.id} cancelled by user.")
                campaign_row = conn.execute("SELECT c.created_at,c.cancellation_requested FROM scan_campaigns c JOIN pipeline_runs r ON r.campaign_id=c.id WHERE r.id=?", (pipeline_run.id,)).fetchone()
                if campaign_row:
                    from datetime import timezone
                    created = datetime.fromisoformat(campaign_row[0])
                    if campaign_row[1]:
                        raise asyncio.CancelledError("Campaign cancellation requested")
                    if (datetime.now(timezone.utc)-created).total_seconds() > self.settings.max_scan_runtime_minutes*60:
                        raise TimeoutError("Campaign runtime safety limit reached")

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
                if prior:
                    from app.config.markets import resolve_market
                    market_res = resolve_market(market)
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
                for index,b in enumerate(candidates):
                    check_cancellation()
                    b.run_id = pipeline_run.id
                    if not b.id:
                        biz_repo.insert(b)
                    if b.id not in observed_ids:
                        ProspectRepository(conn).observe(b, campaign, (run_configuration or {}).get("created_by"))
                    if (index+1)%20==0:
                        emit_event(stage="IDENTITY",event_type="IDENTITY_PROGRESS",message=f"Saved {index+1} of {len(candidates)} canonical observations",completed=index+1,total=len(candidates))
                for r in rejected:
                    r.run_id = pipeline_run.id
                    if not r.id:
                        biz_repo.insert(r)

                pipeline_run.raw_found = raw_total
                pipeline_run.deduped = deduped_total
                pipeline_run.filtered = len(candidates)
                run_repo.update(pipeline_run)
                conn.commit()

                # Limit initial enrichment pool if scanning smaller targets
                pool_multiplier = 4
                candidate_pool_limit = max(target * pool_multiplier, 40)
                active_pool = candidates[:candidate_pool_limit]

                # Stage 5: Website Probing
                check_cancellation()
                PipelineDisplay.print_stage_start(5, 9, "Probing website reachability & security...")
                http_sem = asyncio.Semaphore(self.settings.http_concurrency)

                probe_results: Dict[int, ProbeResult] = {}
                reachable_count = 0
                no_website_count = 0
                probed_count = 0

                emit_event(
                    stage="PROBE",
                    event_type="HTTP_PROGRESS",
                    message=f"Beginning website reachability probe for {len(active_pool)} candidates...",
                    completed=0,
                    total=len(active_pool),
                )

                async def probe_single(b: Business):
                    check_cancellation()
                    nonlocal reachable_count, no_website_count, probed_count
                    if not b.website:
                        b.website_status = "NO_WEBSITE"
                        biz_repo.update(b)
                        conn.commit()
                        no_website_count += 1
                        probed_count += 1
                        return

                    async with http_sem:
                        res = await probe_website(
                            url=b.website,
                            timeout_seconds=self.settings.http.timeout_seconds,
                        )
                        probe_results[b.id] = res
                        if res.reachable:
                            b.website_status = "REACHABLE"
                            reachable_count += 1
                        else:
                            b.website_status = "UNREACHABLE"
                        biz_repo.update(b)
                        probed_count += 1
                        conn.commit()

                        if probed_count % 15 == 0 or probed_count == len(active_pool):
                            emit_event(
                                stage="PROBE",
                                event_type="HTTP_PROGRESS",
                                message=f"{probed_count} / {len(active_pool)} websites probed ({reachable_count} reachable, {no_website_count} no website)",
                                completed=probed_count,
                                total=len(active_pool),
                            )

                probe_tasks = [probe_single(b) for b in active_pool]
                await asyncio.gather(*probe_tasks)
                conn.commit()

                PipelineDisplay.print_stage_success(
                    f"Websites probed: {reachable_count:,} reachable, {no_website_count:,} no website"
                )
                emit_event(
                    stage="PROBE",
                    event_type="HTTP_COMPLETE",
                    message=f"Website probing complete: {reachable_count} reachable, {no_website_count} no website",
                    completed=len(active_pool),
                    total=len(active_pool),
                    metadata={"reachable": reachable_count, "no_website": no_website_count},
                )

                # Stage 6: Crawling Qualified Sites
                check_cancellation()
                PipelineDisplay.print_stage_start(6, 9, "Crawling pages & extracting public contacts...")
                crawl_sem = asyncio.Semaphore(self.settings.crawl_concurrency)
                crawl_results: Dict[int, CrawlResult] = {}
                crawled_count = 0
                crawlable_pool = [b for b in active_pool if b.website and b.id in probe_results and probe_results[b.id].reachable]

                emit_event(
                    stage="CRAWL",
                    event_type="CRAWL_PROGRESS",
                    message=f"Crawling {len(crawlable_pool)} reachable websites for contacts and technical signals...",
                    completed=0,
                    total=len(crawlable_pool),
                )

                async def crawl_single(b: Business):
                    check_cancellation()
                    nonlocal crawled_count
                    probe = probe_results.get(b.id)
                    start_url = probe.final_url if probe and probe.final_url else b.website
                    if not start_url or (probe and not probe.reachable):
                        return
                    async with crawl_sem:
                        cr = await self.crawler.crawl(start_url, initial_html=probe.html_content if probe else None)
                        crawl_results[b.id] = cr
                        crawled_count += 1

                        if crawled_count % 10 == 0 or crawled_count == len(crawlable_pool):
                            emit_event(
                                stage="CRAWL",
                                event_type="CRAWL_PROGRESS",
                                message=f"{crawled_count} / {len(crawlable_pool)} websites crawled",
                                completed=crawled_count,
                                total=len(crawlable_pool),
                            )

                crawl_tasks = [crawl_single(b) for b in active_pool]
                await asyncio.gather(*crawl_tasks)

                PipelineDisplay.print_stage_success(f"Sites crawled: {crawled_count:,}")
                emit_event(
                    stage="CRAWL",
                    event_type="CRAWL_COMPLETE",
                    message=f"Website crawl finished: {crawled_count} sites enriched",
                    completed=crawled_count,
                    total=len(crawlable_pool),
                )

                # Stage 7: Technical, SEO & Lighthouse Audits
                check_cancellation()
                PipelineDisplay.print_stage_start(7, 9, "Executing technical, SEO, and vertical audits...")
                audited_count = 0
                lh_count = 0

                lh_results: Dict[int, LighthouseResult] = {}
                all_findings: Dict[int, List[Finding]] = {}
                all_profiles: Dict[int, WebsiteProfile] = {}

                emit_event(
                    stage="AUDIT",
                    event_type="AUDIT_PROGRESS",
                    message=f"Executing technical and SEO audits for {len(active_pool)} prospects...",
                    completed=0,
                    total=len(active_pool),
                )

                for b in active_pool:
                    check_cancellation()
                    findings: List[Finding] = []
                    profile: Optional[WebsiteProfile] = None

                    if not b.website:
                        findings.append(
                            Finding(
                                business_id=b.id,
                                finding_code="NO_WEBSITE",
                                category="WEBSITE",
                                severity="HIGH",
                                title="No Public Website Found",
                                description="Business has no detectable web presence, losing customer search discovery.",
                                score_points=40,
                            )
                        )
                        profile = WebsiteProfile(
                            business_id=b.id,
                            requested_url="",
                            reachable=False,
                        )
                        profile_repo.upsert(profile)
                        all_profiles[b.id] = profile
                        all_findings[b.id] = findings
                        audited_count += 1
                        conn.commit()
                        continue

                    probe = probe_results.get(b.id)
                    cr = crawl_results.get(b.id) or CrawlResult(start_url=b.website)

                    if probe and not probe.reachable:
                        findings.append(
                            Finding(
                                business_id=b.id,
                                finding_code="SITE_UNREACHABLE",
                                category="WEBSITE",
                                severity="HIGH",
                                title="Website Unreachable",
                                description="Configured business domain could not be loaded over HTTP/HTTPS.",
                                score_points=35,
                            )
                        )
                        profile = WebsiteProfile(
                            business_id=b.id,
                            requested_url=b.website,
                            reachable=False,
                            http_status=probe.http_status,
                        )
                        profile_repo.upsert(profile)
                        all_profiles[b.id] = profile
                        all_findings[b.id] = findings
                        audited_count += 1
                        conn.commit()
                        continue

                    # Run Quick Technical & SEO Audit
                    profile, quick_findings = perform_quick_audit(
                        business_id=b.id,
                        crawl_result=cr,
                        vertical_key=vert_res.key,
                        https_enabled=probe.https_enabled if probe else False,
                        http_status=probe.http_status if probe else 200,
                    )
                    findings.extend(quick_findings)

                    # Vertical-Specific Audits
                    if vert_res.key == "restaurant":
                        findings.extend(audit_restaurant(b.id, profile, cr))
                    elif vert_res.key == "hospitality":
                        findings.extend(audit_hospitality(b.id, profile, cr))
                    elif vert_res.key == "real_estate":
                        findings.extend(audit_real_estate(b.id, profile, cr))

                    # Update Contacts
                    contact_repo.delete_by_business_id(b.id)
                    if cr.contacts.emails:
                        for email, source_url, conf in cr.contacts.emails:
                            _, is_valid = check_email_dns(email)
                            contact_repo.insert(
                                Contact(
                                    business_id=b.id,
                                    contact_type="email",
                                    contact_value=email,
                                    source_url=source_url,
                                    confidence=conf,
                                    is_valid=is_valid,
                                )
                            )
                            if not b.public_email and is_valid:
                                b.public_email = email
                        biz_repo.update(b)

                    if cr.contacts.phones:
                        for phone, source_url, conf in cr.contacts.phones:
                            contact_repo.insert(
                                Contact(
                                    business_id=b.id,
                                    contact_type="phone",
                                    contact_value=phone,
                                    source_url=source_url,
                                    confidence=conf,
                                )
                            )

                    if cr.social_links:
                        if "instagram" in cr.social_links and not b.instagram:
                            b.instagram = cr.social_links["instagram"]
                        if "facebook" in cr.social_links and not b.facebook:
                            b.facebook = cr.social_links["facebook"]
                        if "linkedin" in cr.social_links and not b.linkedin:
                            b.linkedin = cr.social_links["linkedin"]
                        if "x_url" in cr.social_links and not b.x_url:
                            b.x_url = cr.social_links["x_url"]
                        biz_repo.update(b)

                    profile_repo.upsert(profile)
                    finding_repo.delete_by_business_id(b.id)
                    finding_repo.insert_batch(findings)

                    all_profiles[b.id] = profile
                    all_findings[b.id] = findings
                    audited_count += 1
                    conn.commit()

                conn.commit()
                emit_event(
                    stage="AUDIT",
                    event_type="AUDIT_COMPLETE",
                    message=f"Static technical audits complete for {audited_count} businesses",
                    completed=audited_count,
                    total=len(active_pool),
                )

                # Run Lighthouse for promising prospects
                social_results = {}
                has_phase36 = phase36_ready(conn)
                if has_phase36:
                    social_sem = asyncio.Semaphore(self.settings.social_activity_concurrency)
                    async def enrich_one(b):
                        async with social_sem:
                            check_cancellation()
                            cr = crawl_results.get(b.id)
                            profiles, metrics = await enrich_social(cr.all_htmls if cr else {}, b,
                                enabled=self.settings.social_enrichment_enabled and (run_configuration or {}).get('social_enrichment_enabled', True),
                                activity=self.settings.social_activity_enabled and (run_configuration or {}).get('social_activity_enabled', True))
                            store_social(conn, b, profiles)
                            social_results[b.id] = (profiles, metrics)
                            conn.commit()
                    await asyncio.gather(*(enrich_one(b) for b in active_pool))
                    emit_event(stage='CRAWL', event_type='SOCIAL_COMPLETE', message=f"Public social enrichment completed for {len(social_results)} businesses", completed=len(social_results), total=len(active_pool))

                # Run Lighthouse for promising prospects
                if enable_lighthouse and self.settings.audit.lighthouse_enabled:
                    check_cancellation()
                    lh_sem = asyncio.Semaphore(self.settings.lighthouse_concurrency)

                    # Prioritize promising prospects for Lighthouse
                    promising_candidates = []
                    for b in active_pool:
                        p = all_profiles.get(b.id)
                        f = all_findings.get(b.id, [])
                        if p and p.reachable:
                            score_est = sum(item.score_points for item in f)
                            if score_est >= self.settings.audit.preliminary_score_threshold:
                                promising_candidates.append((b, score_est))

                    # Sort by highest preliminary opportunity
                    promising_candidates.sort(key=lambda x: x[1], reverse=True)
                    lh_pool = [x[0] for x in promising_candidates[:min(target, self.settings.max_lighthouse_audits, (run_configuration or {}).get("lighthouse_budget", self.settings.max_lighthouse_audits))]]

                    if lh_pool:
                        emit_event(
                            stage="LIGHTHOUSE",
                            event_type="LIGHTHOUSE_PROGRESS",
                            message=f"Initiating Lighthouse deep audits for top {len(lh_pool)} prospects...",
                            completed=0,
                            total=len(lh_pool),
                        )

                    async def run_lh_single(b: Business):
                        nonlocal lh_count
                        p = all_profiles.get(b.id)
                        if not p or not p.reachable:
                            return

                        async with lh_sem:
                            res = await run_lighthouse_audit(
                                business_id=b.id,
                                target_url=p.final_url or b.website,
                                timeout_seconds=self.settings.audit.lighthouse_timeout_seconds,
                            )
                            if res:
                                lh_repo.upsert(res)
                                lh_results[b.id] = res
                                conn.commit()
                                lh_count += 1
                                if lh_count % 5 == 0 or lh_count == len(lh_pool):
                                    emit_event(
                                        stage="LIGHTHOUSE",
                                        event_type="LIGHTHOUSE_PROGRESS",
                                        message=f"{lh_count} / {len(lh_pool)} Lighthouse audits completed",
                                        completed=lh_count,
                                        total=len(lh_pool),
                                    )

                    lh_tasks = [run_lh_single(b) for b in lh_pool]
                    await asyncio.gather(*lh_tasks)
                    conn.commit()

                    emit_event(
                        stage="LIGHTHOUSE",
                        event_type="LIGHTHOUSE_COMPLETE",
                        message=f"Lighthouse deep audits finished ({lh_count} successful)",
                        completed=lh_count,
                        total=len(lh_pool),
                    )

                PipelineDisplay.print_stage_success(
                    f"Audits complete: {audited_count:,} static audits, {lh_count:,} Lighthouse deep scans"
                )

                # Stage 8: Lead Scoring & Ranking
                check_cancellation()
                PipelineDisplay.print_stage_start(8, 9, "Calculating opportunity scores & ranking prospects...")
                emit_event(
                    stage="SCORING",
                    event_type="SCORING_STARTED",
                    message="Calculating opportunity scores and ranking prospects...",
                )

                qualified_leads = []
                a_plus_count = 0
                a_count = 0
                b_count = 0
                fit_preferences = {}

                for b in active_pool:
                    p = all_profiles.get(b.id)
                    lh = lh_results.get(b.id)
                    f = all_findings.get(b.id, [])

                    lead_score = calculate_lead_score(
                        business=b,
                        profile=p,
                        lighthouse=lh,
                        findings=f,
                        has_valid_email=bool(b.public_email),
                        has_contact_form=bool(p and p.has_contact_page),
                    )
                    opportunity = analyze_opportunities(b, p, lh, crawl_results.get(b.id), probe_results.get(b.id), (run_configuration or {}).get("opportunities"))
                    lead_score.score_breakdown["opportunities"] = opportunity
                    store_opportunities(conn, b, opportunity)
                    existing_codes = {item.finding_code for item in f}
                    for kind, items in opportunity["evidence"].items():
                        for item in items:
                            if item["code"] not in existing_codes:
                                f.append(Finding(business_id=b.id, finding_code=item["code"], category=kind, severity="HIGH" if item["points"] >= 15 else "MEDIUM" if item["points"] >= 5 else "LOW", title=item["code"].replace("_", " ").title(), description=item["detail"], evidence=item["detail"], source_url=b.website, score_points=item["points"]))
                                existing_codes.add(item["code"])
                    finding_repo.delete_by_business_id(b.id)
                    finding_repo.insert_batch(f)
                    counts = footprint_counts(conn, b)
                    cr = crawl_results.get(b.id)
                    scale, scale_reason, scale_confidence = classify_scale_v2(b, *counts, pages=cr.all_htmls if cr else {})
                    if has_phase36:
                        fit, fit_reason = commercial_fit(b, scale, opportunity['contactability_level'], p)
                        social_profiles, social_metrics = social_results.get(b.id, ([], {}))
                        store_intelligence(conn, b, scale, scale_reason, scale_confidence, dict(locations=counts[0], cities=counts[1], regions=counts[2]), fit, fit_reason, presence_summary(social_profiles) if social_metrics.get('enabled',True) else 'UNKNOWN', social_metrics)
                        # A modest public-footprint preference, never a hard
                        # exclusion of a local business with strong evidence.
                        if (run_configuration or {}).get('quality') in ('balanced','high_intent'):
                            fit_preferences[b.id] = (8 if scale=='MID_MARKET' else 5 if scale=='SMALL_GROUP' else 0) + (3 if fit=='HIGH' else 0)
                    conn.execute("UPDATE prospects SET business_scale=?,scale_reason=?,scale_confidence=? WHERE id=(SELECT prospect_id FROM businesses WHERE id=?)", (scale, scale_reason, scale_confidence, b.id))
                    attach_workflow(conn, b.id, lead_score)
                    score_repo.upsert(lead_score)

                    # Qualification check:
                    # 1. Active-looking relevant business
                    # 2. Opportunity exists (score >= 35 or no website)
                    # 3. Has at least one contact channel
                    has_contact = bool(
                        b.public_email or b.phone or b.normalized_phone or b.instagram or b.facebook or (p and p.has_contact_page)
                    )
                    has_opportunity = lead_score.total_score >= 35.0 or not b.website
                    if run_configuration and "quality" in run_configuration:
                        policy = quality_modes()[run_configuration["quality"]]
                        values = {"WEBSITE": opportunity["website_opportunity_score"], "SEO": opportunity["seo_opportunity_score"], "SECURITY": opportunity["security_opportunity_score"]}
                        has_opportunity = any((values[kind] or 0) >= policy["threshold"] for kind in run_configuration["opportunities"])
                        has_contact = opportunity["contactability_level"] != "LOW" if policy["contact_required"] else True
                        has_opportunity = has_opportunity and scale in run_configuration["business_scales"]
                        if policy["certain_vertical_required"]:
                            has_opportunity = has_opportunity and b.vertical_validation_status == "VALID" and scale not in ["ENTERPRISE", "KNOWN_CHAIN"]
                        if run_configuration["results"] == "new":
                            first_campaign = conn.execute("SELECT p.first_campaign_id FROM prospects p JOIN businesses b ON b.prospect_id=p.id WHERE b.id=?", (b.id,)).fetchone()[0]
                            has_opportunity = has_opportunity and first_campaign == run_configuration["request_id"]

                    if has_opportunity and has_contact:
                        b.processing_status = ProcessingStatus.QUALIFIED.value
                        biz_repo.update(b)
                        qualified_leads.append((b, lead_score, p, lh, f))

                        if lead_score.tier == "A+":
                            a_plus_count += 1
                        elif lead_score.tier == "A":
                            a_count += 1
                        elif lead_score.tier == "B":
                            b_count += 1

                conn.commit()

                # Sort qualified leads primarily by total_score DESC, contactability DESC, source_confidence DESC
                qualified_leads.sort(
                    key=lambda x: (
                        max((x[1].score_breakdown.get("opportunities", {}) or {}).get("website_opportunity_score", 0) or 0, x[1].total_score) + fit_preferences.get(x[0].id, 0),
                        x[1].contactability_score,
                        x[0].source_confidence,
                    ),
                    reverse=True,
                )

                # Limit to target
                exported_leads = qualified_leads[:target]
                if has_phase36:
                    from app.enrichment.screenshot import capture_website
                    # Capture only the final shortlist, sequentially, within the
                    # existing scan worker. No browser is launched by PDF jobs.
                    for business, _, profile, _, _ in exported_leads:
                        check_cancellation()
                        await capture_website(conn, business, profile, crawl_results.get(business.id))
                        conn.commit()
                PipelineDisplay.print_stage_success(
                    f"Qualified: {len(qualified_leads):,} prospects (A+: {a_plus_count:,}, A: {a_count:,}, B: {b_count:,})"
                )
                emit_event(
                    stage="SCORING",
                    event_type="SCORING_COMPLETE",
                    message=f"Qualified {len(qualified_leads)} prospects (A+: {a_plus_count}, A: {a_count}, B: {b_count})",
                    completed=len(qualified_leads),
                    total=len(active_pool),
                    metadata={
                        "qualified": len(qualified_leads),
                        "a_plus": a_plus_count,
                        "a": a_count,
                        "b": b_count,
                    },
                )

                # Stage 9: Exporting
                check_cancellation()
                PipelineDisplay.print_stage_start(9, 9, "Generating finalized XLSX & CSV exports...")
                timestamp_str = datetime.now().strftime("%Y-%m-%d")
                clean_market_name = "".join(c if c.isalnum() else "_" for c in market)
                clean_market_name = clean_market_name.replace("__", "_").strip("_")
                clean_vert_name = vert_res.key.title()

                excel_path = output_dir / f"{clean_market_name}_{clean_vert_name}_{pipeline_run.id}.xlsx"
                csv_path = output_dir / f"{clean_market_name}_{clean_vert_name}_{pipeline_run.id}.csv"

                # Export Excel
                export_leads_to_excel(
                    run_info=pipeline_run,
                    qualified_leads=exported_leads,
                    all_discovered=candidates,
                    rejected_businesses=rejected,
                    output_path=excel_path,
                )

                # Export CSV
                export_leads_to_csv(
                    leads=exported_leads,
                    output_path=csv_path,
                )
                campaign_id = conn.execute("SELECT campaign_id FROM pipeline_runs WHERE id=?", (pipeline_run.id,)).fetchone()[0] or "legacy"
                base_key = f"campaigns/{campaign_id}/runs/{pipeline_run.id}"
                publish_artifact(conn, base_key+"/leads.xlsx", excel_path, run_id=pipeline_run.id, kind="xlsx")
                publish_artifact(conn, base_key+"/leads.csv", csv_path, run_id=pipeline_run.id, kind="csv")
                for business_id, result in lh_results.items():
                    if result.raw_report_path and Path(result.raw_report_path).is_file():
                        publish_artifact(conn, f"audits/{pipeline_run.id}/{business_id}/lighthouse.json", result.raw_report_path, run_id=pipeline_run.id, business_id=business_id, kind="lighthouse")

                PipelineDisplay.print_stage_success(f"Exported: {len(exported_leads):,} prospects to Excel and CSV")
                emit_event(
                    stage="EXPORT",
                    event_type="EXPORT_COMPLETE",
                    message=f"Exported {len(exported_leads)} prospects to Excel & CSV files",
                    completed=len(exported_leads),
                    total=len(exported_leads),
                    metadata={"excel": str(excel_path), "csv": str(csv_path)},
                )

                # Finalize run status
                runtime = time.time() - start_time
                pipeline_run.finished_at = datetime.now().isoformat()
                pipeline_run.status = "COMPLETED"
                pipeline_run.websites_processed = audited_count
                pipeline_run.qualified = len(qualified_leads)
                pipeline_run.exported = len(exported_leads)
                pipeline_run.output_file = str(excel_path)
                run_repo.update(pipeline_run)
                conn.commit()

                emit_event(
                    stage="COMPLETION",
                    event_type="RUN_COMPLETED",
                    message=f"Pipeline run #{pipeline_run.id} finished successfully in {runtime:.1f}s",
                    completed=len(exported_leads),
                    total=target,
                    metadata={"runtime_seconds": round(runtime, 2)},
                )

                # Display rich summary
                PipelineDisplay.print_run_summary(
                    market=market,
                    vertical=vert_res.display_name,
                    target=target,
                    raw_found=pipeline_run.raw_found,
                    deduped=pipeline_run.deduped,
                    filtered=pipeline_run.filtered,
                    websites=reachable_count,
                    no_websites=no_website_count,
                    audited=audited_count,
                    qualified=len(qualified_leads),
                    a_plus=a_plus_count,
                    a=a_count,
                    b=b_count,
                    exported=len(exported_leads),
                    output_xlsx=str(excel_path),
                    output_csv=str(csv_path),
                    runtime_sec=runtime,
                )

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
