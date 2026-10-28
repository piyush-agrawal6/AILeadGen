"""Deterministic acceptance data. Refused outside explicit test environment."""
import re
from pathlib import Path
from app.config.settings import get_settings
from app.database.connection import db_session
from app.database.models import Business, WebsiteProfile, PipelineRunEvent
from app.database.repositories import BusinessRepository, PipelineRunRepository, PipelineRunEventRepository, WebsiteProfileRepository, LeadScoreRepository
from app.database.prospects import ProspectRepository, now
from app.enrichment.crawler import CrawlResult
from app.enrichment.http_probe import ProbeResult
from app.scoring.scorer import calculate_lead_score
from app.scoring.opportunities import analyze_opportunities, store_opportunities
from app.exports.phase3 import attach_workflow
from app.exports.csv_export import export_leads_to_csv
from app.exports.excel_export import export_leads_to_excel
from app.storage import publish_artifact


def run_fixture(run_id):
    if get_settings().app_env != "test":
        raise RuntimeError("Deterministic fixtures are forbidden outside test mode")
    with db_session() as conn:
        runs=PipelineRunRepository(conn)
        run=runs.get_by_id(run_id)
        if not run or run.status == "COMPLETED": return run
        run.status="RUNNING";runs.update(run);conn.commit()
        campaign=conn.execute("SELECT campaign_id FROM pipeline_runs WHERE id=?",(run_id,)).fetchone()[0]
        events=PipelineRunEventRepository(conn)
        events.create(PipelineRunEvent(run_id=run_id,stage="DISCOVERY",event_type="FIXTURE_STARTED",message="Deterministic test evidence; no public sites contacted."))
        leads=[]
        for index in range(min(run.target,5)):
            if conn.execute("SELECT cancellation_requested FROM pipeline_runs WHERE id=?",(run_id,)).fetchone()[0]:
                run.status="CANCELLED";runs.update(run);return run
            slug=re.sub(r"[^a-z0-9]+","-",run.market.lower())+"-"+run.vertical+"-"+str(index)
            source="fixture:"+slug
            existing=conn.execute("SELECT id FROM businesses WHERE run_id=? AND external_osm_id=?",(run_id,source)).fetchone()
            b=BusinessRepository(conn).get_by_id(existing[0]) if existing else Business(name=f"Fixture {run.vertical.replace('_',' ').title()} {index+1}",normalized_name=slug,vertical=run.vertical,city=run.market.split(',')[0],country="United States",country_code="US",phone="+15125550123",public_email="info@"+slug+".example",website=None if index==0 else "https://"+slug+".example",domain=None if index==0 else slug+".example",run_id=run_id,external_osm_id=source,processing_status="QUALIFIED")
            if not b.id:BusinessRepository(conn).insert(b)
            ProspectRepository(conn).observe(b,campaign,(run.run_configuration or {}).get("created_by"))
            profile=WebsiteProfile(business_id=b.id,requested_url=b.website or "",http_status=200 if b.website else None,reachable=bool(b.website),https_enabled=True,has_viewport=True,has_h1=True,h1_count=1,has_contact_page=True)
            WebsiteProfileRepository(conn).upsert(profile)
            crawl=CrawlResult(b.website or "")
            crawl.all_htmls[b.website or ""]='<h1>Independent local business</h1><meta name="robots" content="noindex"><a href="/book">Book an appointment</a><form action="http://public.example/contact"></form>'
            probe=ProbeResult(requested_url=b.website or "",reachable=bool(b.website),response_headers={"server":"fixture/1.0"})
            opportunity=analyze_opportunities(b,profile,None,crawl,probe)
            store_opportunities(conn,b,opportunity)
            score=calculate_lead_score(b,profile,None,[],has_valid_email=True,has_contact_form=True)
            score.score_breakdown["opportunities"]=opportunity
            attach_workflow(conn,b.id,score)
            LeadScoreRepository(conn).upsert(score)
            leads.append((b,score,profile,None,[]))
        directory=Path("output/fixtures");directory.mkdir(parents=True,exist_ok=True)
        xlsx=directory/f"run-{run_id}.xlsx";csv=directory/f"run-{run_id}.csv"
        export_leads_to_excel(run,leads,[item[0] for item in leads],[],xlsx)
        export_leads_to_csv(leads,csv)
        for kind,path in [("xlsx",xlsx),("csv",csv)]:publish_artifact(conn,f"campaigns/{campaign or 'legacy'}/runs/{run_id}/leads.{kind}",path,run_id=run_id,kind=kind)
        run.status="COMPLETED";run.raw_found=len(leads);run.qualified=len(leads);run.exported=len(leads);run.output_file=str(xlsx);run.finished_at=now();runs.update(run)
        events.create(PipelineRunEvent(run_id=run_id,stage="COMPLETION",event_type="RUN_COMPLETED",message="Deterministic fixture completed.",completed=len(leads),total=len(leads)))
        return run
