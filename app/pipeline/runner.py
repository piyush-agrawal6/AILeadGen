import asyncio
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
    ProcessingStatus,
    WebsiteProfile,
)
from app.database.repositories import (
    BusinessRepository,
    ContactRepository,
    FindingRepository,
    LeadScoreRepository,
    LighthouseRepository,
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

logger = logging.getLogger("leadengine.pipeline.runner")


class PipelineRunner:
    def __init__(self, db_path: Optional[Path] = None, output_dir: Optional[Path] = None):
        self.settings = get_settings()
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
    ) -> PipelineRun:
        """Execute the end-to-end LeadEngine discovery and qualification pipeline."""
        start_time = time.time()
        output_dir = self.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        with db_session(self.db_path) as conn:
            from app.database.migrations import run_migrations
            run_migrations(conn)
            run_repo = PipelineRunRepository(conn)
            biz_repo = BusinessRepository(conn)
            profile_repo = WebsiteProfileRepository(conn)
            contact_repo = ContactRepository(conn)
            lh_repo = LighthouseRepository(conn)
            finding_repo = FindingRepository(conn)
            score_repo = LeadScoreRepository(conn)

            # 1. Setup or resume PipelineRun
            if run_id:
                pipeline_run = run_repo.get_by_id(run_id)
                if not pipeline_run:
                    raise ValueError(f"Pipeline run #{run_id} not found to resume.")
                PipelineDisplay.print_stage_start(1, 9, f"Resuming Pipeline Run #{run_id}...")
            else:
                pipeline_run = PipelineRun(
                    market=market,
                    vertical=vertical,
                    target=target,
                    status="RUNNING",
                )
                pipeline_run.id = run_repo.create(pipeline_run)
            conn.commit()

            # Stage 1: Market Resolution
            PipelineDisplay.print_stage_start(1, 9, f"Resolving market '{market}'...")
            market_res, vert_res, candidates, rejected = self.discovery_coord.discover(
                market_str=market,
                vertical_str=vertical,
                target_leads=target,
                include_chains=include_chains,
            )
            PipelineDisplay.print_stage_success(
                f"Market resolved: {market_res.city}, {market_res.state} {market_res.country} "
                f"(lat: {market_res.center_lat:.3f}, lon: {market_res.center_lon:.3f})"
            )

            # Stage 2 & 3: Discovery & Deduplication results
            PipelineDisplay.print_stage_start(2, 9, "Discovering public businesses...")
            PipelineDisplay.print_stage_success(f"Discovered: {len(candidates) + len(rejected):,} raw listings")

            PipelineDisplay.print_stage_start(3, 9, "Deduplicating & normalising...")
            PipelineDisplay.print_stage_success(f"{len(candidates):,} unique candidate businesses")

            PipelineDisplay.print_stage_start(4, 9, "Filtering franchise chains & invalid entities...")
            PipelineDisplay.print_stage_success(f"{len(candidates):,} valid prospect candidates")

            # Persist discovered candidates and rejected entities
            for b in candidates:
                biz_repo.insert(b)
            for r in rejected:
                biz_repo.insert(r)

            pipeline_run.raw_found = len(candidates) + len(rejected)
            pipeline_run.deduped = len(candidates)
            pipeline_run.filtered = len(candidates)
            run_repo.update(pipeline_run)
            conn.commit()

            # Limit initial enrichment pool if scanning smaller targets
            pool_multiplier = 4
            candidate_pool_limit = max(target * pool_multiplier, 40)
            active_pool = candidates[:candidate_pool_limit]

            # Stage 5: Website Probing
            PipelineDisplay.print_stage_start(5, 9, "Probing website reachability & security...")
            http_sem = asyncio.Semaphore(self.settings.http_concurrency)

            probe_results: Dict[int, ProbeResult] = {}
            reachable_count = 0
            no_website_count = 0

            async def probe_single(b: Business):
                nonlocal reachable_count, no_website_count
                if not b.website:
                    no_website_count += 1
                    return
                async with http_sem:
                    res = await probe_website(
                        url=b.website,
                        timeout_seconds=self.settings.http.timeout_seconds,
                    )
                    probe_results[b.id] = res
                    if res.reachable:
                        reachable_count += 1

            probe_tasks = [probe_single(b) for b in active_pool]
            await asyncio.gather(*probe_tasks)

            PipelineDisplay.print_stage_success(
                f"Websites probed: {reachable_count:,} reachable, {no_website_count:,} no website"
            )

            # Stage 6: Crawling Qualified Sites
            PipelineDisplay.print_stage_start(6, 9, "Crawling pages & extracting public contacts...")
            crawl_sem = asyncio.Semaphore(self.settings.crawl_concurrency)
            crawl_results: Dict[int, CrawlResult] = {}
            crawled_count = 0

            async def crawl_single(b: Business):
                nonlocal crawled_count
                probe = probe_results.get(b.id)
                start_url = probe.final_url if probe and probe.final_url else b.website
                if not start_url or (probe and not probe.reachable):
                    return
                async with crawl_sem:
                    cr = await self.crawler.crawl(start_url, initial_html=probe.html_content if probe else None)
                    crawl_results[b.id] = cr
                    crawled_count += 1

            crawl_tasks = [crawl_single(b) for b in active_pool]
            await asyncio.gather(*crawl_tasks)

            PipelineDisplay.print_stage_success(f"Sites crawled: {crawled_count:,}")

            # Stage 7: Technical, SEO & Lighthouse Audits
            PipelineDisplay.print_stage_start(7, 9, "Executing technical, SEO, and vertical audits...")
            audited_count = 0
            lh_count = 0

            lh_results: Dict[int, LighthouseResult] = {}
            all_findings: Dict[int, List[Finding]] = {}
            all_profiles: Dict[int, WebsiteProfile] = {}

            for b in active_pool:
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

            # Run Lighthouse for promising prospects
            if enable_lighthouse and self.settings.audit.lighthouse_enabled:
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
                lh_pool = [x[0] for x in promising_candidates[:target]]

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
                            lh_count += 1

                lh_tasks = [run_lh_single(b) for b in lh_pool]
                await asyncio.gather(*lh_tasks)

            PipelineDisplay.print_stage_success(
                f"Audits complete: {audited_count:,} static audits, {lh_count:,} Lighthouse deep scans"
            )

            # Stage 8: Lead Scoring & Ranking
            PipelineDisplay.print_stage_start(8, 9, "Calculating opportunity scores & ranking prospects...")
            qualified_leads = []
            a_plus_count = 0
            a_count = 0
            b_count = 0

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
                score_repo.upsert(lead_score)

                # Qualification check:
                # 1. Active-looking relevant business
                # 2. Opportunity exists (score >= 35 or no website)
                # 3. Has at least one contact channel
                has_contact = bool(
                    b.public_email or b.phone or b.normalized_phone or b.instagram or b.facebook or (p and p.has_contact_page)
                )
                has_opportunity = lead_score.total_score >= 35.0 or not b.website

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
                    x[1].total_score,
                    x[1].contactability_score,
                    x[0].source_confidence,
                ),
                reverse=True,
            )

            # Limit to target
            exported_leads = qualified_leads[:target]
            PipelineDisplay.print_stage_success(
                f"Qualified: {len(qualified_leads):,} prospects (A+: {a_plus_count:,}, A: {a_count:,}, B: {b_count:,})"
            )

            # Stage 9: Exporting
            PipelineDisplay.print_stage_start(9, 9, "Generating finalized XLSX & CSV exports...")
            timestamp_str = datetime.now().strftime("%Y-%m-%d")
            clean_market_name = "".join(c if c.isalnum() else "_" for c in market)
            clean_market_name = clean_market_name.replace("__", "_").strip("_")
            clean_vert_name = vert_res.key.title()

            excel_path = output_dir / f"{clean_market_name}_{clean_vert_name}_{timestamp_str}.xlsx"
            csv_path = output_dir / f"{clean_market_name}_{clean_vert_name}_{timestamp_str}.csv"

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

            PipelineDisplay.print_stage_success(f"Exported: {len(exported_leads):,} prospects to Excel and CSV")

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
