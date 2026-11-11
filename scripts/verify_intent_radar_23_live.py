"""Bounded genuine official API/feed acceptance in a NEW disposable database."""
import argparse
import json
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.config.settings import get_settings
from app.database.connection import get_connection
from app.database.migrations import run_migrations
from app.api.organization import create_organization
from app.platform.context import workspace_scope
from app.intent_radar import models,service,discovery,connectors
from app.intelligence import jobs
from fastapi import HTTPException

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--database',required=True)
parser.add_argument('--public-meta-feed',action='store_true',help='Include public Discourse Meta latest.rss for local read-only transport evaluation; commercial approval remains pending')
parser.add_argument('--hn-jobs',action='store_true',help='Explicit read-only opt-in job feed coverage evaluation, not default buyer-intent discovery')
args=parser.parse_args();path=Path(args.database).resolve()
base=Path('/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode').resolve()
assert path.is_relative_to(base) and path.parent.is_dir() and not path.exists()
s=get_settings();s.app_env='test';s.database_path=str(path);s.database_url='';s.intent_radar_stage='Beta';s.intent_radar_ai_enabled=False
# Local read-only official API evaluation; commercial rollout still needs terms review.
s.intent_radar_stackexchange_enabled=True;s.intent_radar_approved_feed_hosts='www.w3.org'+(';meta.discourse.org' if args.public_meta_feed else '')
s.allowed_user_emails='radar23@example.test'
c=get_connection(path);run_migrations(c);actor='radar23@example.test'
org=create_organization(c,actor,'Disposable Radar 23 acceptance')['organization_id'];other=create_organization(c,actor,'Foreign test workspace')['organization_id']
c.execute("UPDATE organization_onboarding SET status='COMPLETED' WHERE organization_id IN (?,?)",(org,other))
c.execute("UPDATE organization_products SET enabled=1 WHERE product='INTENT_RADAR' AND organization_id IN (?,?)",(org,other));c.commit()
reports=[]
with workspace_scope(c,actor,org):
    feed=connectors.configure(c,models.SourceConfig(name='W3C news',family='rss',endpoint='https://www.w3.org/news/feed/',policy_reference='https://www.w3.org/copyright/document-license-2023/',attribution='Copyright © 2026 World Wide Web Consortium. https://www.w3.org/copyright/document-license-2023/ · original news excerpts',enabled=True));c.commit()
    configs=[models.Search(keywords=['ask hn']),models.Search(keywords=['show hn'],hn_feeds=['show']),models.Search(keywords=['python'],sources=['stack_exchange']),models.Search(keywords=['web'],sources=['rss'],feed_ids=[feed['id']]),models.Search(keywords=['web'],sources=['hacker_news','stack_exchange','rss'],feed_ids=[feed['id']])]
    configs.append(models.Search(keywords=['the'],hn_feeds=['new','top','best'],hn_comments=True))
    if args.hn_jobs:configs.append(models.Search(keywords=['hiring'],hn_feeds=['jobs']))
    if args.public_meta_feed:
        meta=connectors.configure(c,models.SourceConfig(name='Discourse Meta public latest',family='discourse',endpoint='https://meta.discourse.org/latest.rss',policy_reference='https://meta.discourse.org/robots.txt · latest.rss not disallowed; bounded local transport evaluation only; commercial terms approval pending',attribution='Discourse Meta public discussions · original linked topic and permitted excerpt; no private content',enabled=True));c.commit()
        configs.append(models.Search(keywords=['discourse'],sources=['discourse'],feed_ids=[meta['id']]))
    for q in configs:
        start=time.monotonic();job=discovery.create(c,models.Discovery(configuration=q));submission=time.monotonic()-start;c.commit();jobs.execute(job['id'],path)
        result=discovery.owned_job(c,job['id'])
        reports.append({'sources':q.sources,'feeds':q.hn_feeds,'job_status':result['status'],'submission_ms':round(submission*1000,2),'completion_seconds':round(time.monotonic()-start,2),'items':result['items'],'source_runs':result['sources']})
    signals=service.listing(c,'signals',size=100)['items'];count=len(signals)
    # Repeated same query must reuse safe cache/native identities.
    q=configs[4];job=discovery.create(c,models.Discovery(configuration=q));c.commit();jobs.execute(job['id'],path)
    assert service.listing(c,'signals',size=100)['total']>=count
    assert c.execute('SELECT COUNT(*) FROM intent_signals').fetchone()[0]==c.execute('SELECT COUNT(DISTINCT source || source_record_id) FROM intent_signals').fetchone()[0]
    samples=[{'source':x['source'],'title':x['title'],'url':x['source_url'],'published_at':x['observed_at']} for x in signals]
with workspace_scope(c,actor,other):
    assert service.listing(c,'signals')['total']==0
    if signals:
        try:service.get(c,'signals',signals[0]['id'])
        except HTTPException as exc:assert exc.status_code==404
        else:raise AssertionError('Cross-tenant read allowed')
        try:service.bookmark(c,signals[0]['id'])
        except HTTPException as exc:assert exc.status_code==404
        else:raise AssertionError('Cross-tenant write allowed')
for table in ('businesses','contact_people','email_messages','workflow_runs'):assert c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0
print(json.dumps({'database':str(path),'reports':reports,'samples':samples,'cross_tenant_denied':True,'lead_engine_or_mail_records_created':0,'commercial_stackexchange_approval':'Pending API terms review; test enablement only'},indent=2))
c.close()
