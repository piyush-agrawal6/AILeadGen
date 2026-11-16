"""Stage/promote the verified non-chargeable product release on existing resources.

No migrations, financial writes, data cleanup, IAM changes, secret replacement,
signup activation, scheduler changes or frontend hosting changes are performed.
Staging and promotion are separate so real read/worker acceptance can intervene.
"""
import argparse,copy,hashlib,hmac,json,os,secrets,subprocess,time
from pathlib import Path
import xml.etree.ElementTree as ET
import httpx
from dotenv import dotenv_values
from scripts.deploy_beta_backend import command,REGION,OPERATOR_ENV
from scripts.deploy_growth_release import spec
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/artifacts/verification'/os.environ.get('PLANEBYTE_RELEASE_EVIDENCE','final-product')
RESOURCES=[('services','leadengine-api','api'),('jobs','leadengine-worker','worker'),('jobs','leadengine-acquisition','worker'),('jobs','leadengine-quota-canary','worker')]
ORIGIN='https://leadengine-api-befca7xg4a-el.a.run.app'

def app_hash():
    digest=hashlib.sha256()
    for p in sorted((ROOT/'app').rglob('*')):
        if p.is_file() and p.suffix in ('.py','.json'):digest.update(str(p.relative_to(ROOT)).encode()+b'\0'+p.read_bytes()+b'\0')
    return digest.hexdigest()

def frontend_hash():
    digest=hashlib.sha256()
    for base in ('app','components','lib','public'):
        for p in sorted((ROOT/'dashboard'/base).rglob('*')):
            if p.is_file() and (base=='public' or p.suffix in ('.tsx','.ts','.css','.json')):
                digest.update(str(p.relative_to(ROOT)).encode()+b'\0'+p.read_bytes()+b'\0')
    for name in ('auth.ts','proxy.ts','next.config.mjs','package.json','package-lock.json'):
        p=ROOT/'dashboard'/name
        if p.is_file():digest.update(str(p.relative_to(ROOT)).encode()+b'\0'+p.read_bytes()+b'\0')
    return digest.hexdigest()

def save(path,value):
    path.write_text(json.dumps(value,indent=2));path.chmod(0o600)

def gate():
    if OUT.name=='final' and OUT.parent.name=='public-launch':
        return public_launch_gate()
    frozen=json.loads((OUT/'frozen-source.json').read_text())
    if app_hash()!=frozen['app_sha256']:raise RuntimeError('Backend changed after the frozen test run.')
    report=ET.parse(OUT/'backend-approved.xml').getroot();suites=list(report) if report.tag=='testsuites' else [report]
    if sum(int(s.get('tests',0)) for s in suites)<1030 or any(int(s.get('failures',0))+int(s.get('errors',0)) for s in suites):raise RuntimeError('Full backend gate is not passing.')
    browser=json.loads((OUT/'browser-results.json').read_text())['stats']
    final=OUT.name=='final-remediation'
    if browser.get('unexpected',1) or browser.get('expected')!=(10 if final else 7) or browser.get('skipped',0):raise RuntimeError('Product assistant and responsive browser gate is not passing.')
    if 'Compiled successfully' not in (OUT/('frontend-build-final.log' if final else 'frontend-approved.log')).read_text():raise RuntimeError('Verified frontend build missing.')
    for name in (('frontend-types-final.log' if final else 'types-approved.log'),):
        if (OUT/name).read_text().strip():raise RuntimeError('Frontend type gate is not passing.')
    units=(OUT/('frontend-units-final.log' if final else 'units-approved.log')).read_text()
    if 'failed' in units.lower() or ('165 passed' if final else '159 passed') not in units:raise RuntimeError('Frontend unit gate is not passing.')
    if final:
        onboarding=json.loads((OUT/'onboarding-browser-results.json').read_text())['stats']
        if onboarding.get('unexpected',1) or onboarding.get('expected')!=2 or onboarding.get('skipped',0):raise RuntimeError('Reviewed onboarding browser acceptance is not passing.')
        if frontend_hash()!=json.loads((OUT/'frontend-frozen.json').read_text())['frontend_sha256']:raise RuntimeError('Frontend changed after visual/browser acceptance.')
        required={'test_postgres_reviewed_setup_worker_replay_defaults_and_no_automatic_actions','test_ai_setup_review_resume_approval_shared_defaults_and_completion_without_actions','test_scoped_references_viewer_absent_context_and_private_guidance','test_dispatch_claim_is_bounded_recoverable_and_fenced_from_late_acknowledgements','test_global_setup_dispatch_capacity_has_a_bounded_queue_without_provider_work','test_revoked_dispatch_candidate_does_not_starve_other_workspaces','test_postgres_overview_snapshot_equivalence_retention_and_tenant_scope','test_postgres_assistant_count_reads_are_ai_free_and_do_not_create_jobs','test_transaction_configuration_is_reapplied_after_commit_and_rollback','test_crash_recovery_cannot_refund_a_previous_unknown_attempt','test_queued_report_cancellation_refunds_unstarted_shared_capacity','test_slow_count_database_work_keeps_the_http_event_loop_responsive','test_dispatch_preparation_is_offloaded_with_verified_context','test_postgres_overview_summary_matches_scoped_counts_and_retention','test_incomplete_thinking_usage_remains_reserved_instead_of_becoming_zero'}
        passed={case.get('name') for case in report.iter('testcase') if not any(case.find(tag) is not None for tag in ('failure','error','skipped'))}
        if not required<=passed:raise RuntimeError('New critical backend regressions did not pass in the frozen full run.')
        recovery=json.loads((OUT/'recovery-proof.json').read_text())
        if not recovery.get('restored_exactly') or recovery.get('row_loss') or recovery.get('second_migration_run')!=0:raise RuntimeError('Fresh recovery rehearsal is not verified.')
    if subprocess.check_output(['git','status','--porcelain','--','app'],cwd=ROOT,text=True).strip():raise RuntimeError('Backend application must be committed exactly before staging.')
    if subprocess.check_output(['git','diff','--diff-filter=D','--name-only','a608210','HEAD'],cwd=ROOT,text=True).strip():raise RuntimeError('Unexpected source deletion requires investigation.')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()

def public_launch_gate():
    """Independent frozen acceptance for the newer, flag-off launch candidate."""
    frozen=json.loads((OUT/'frozen-source.json').read_text())
    if frozen['app_sha256']!=app_hash() or frozen['frontend_sha256']!=frontend_hash():raise RuntimeError('Application changed after frozen launch acceptance.')
    report=ET.parse(OUT/'backend-approved.xml').getroot();suites=list(report) if report.tag=='testsuites' else [report]
    if sum(int(s.get('tests',0)) for s in suites)<1140 or any(int(s.get('failures',0))+int(s.get('errors',0)) for s in suites):raise RuntimeError('Combined backend/PostgreSQL acceptance is not passing.')
    passed={case.get('name') for case in report.iter('testcase') if not any(case.find(tag) is not None for tag in ('failure','error','skipped'))}
    required={'test_postgres_customer_verification_concurrency_revocation_and_quota','test_postgres_fixed_term_fulfillment_race_and_refund_preserves_history','test_google_signup_cannot_bypass_disabled_native_access_enforcement','test_verified_closure_is_operator_only_tracks_deadlines_and_retains_history','test_signed_bootstrap_exact_paths_redacts_secrets_and_binds_session','test_callback_hash_duplicate_and_tampering','test_payu_refund_lookup_is_read_only_and_does_not_infer_currency'}
    if not required<=passed:raise RuntimeError('Critical launch security/payment cases are missing.')
    for filename,count in (('browser-results.json',10),('accounts-browser-results.json',1),('onboarding-browser-results.json',2)):
        stats=json.loads((OUT/filename).read_text())['stats']
        if stats.get('expected')!=count or stats.get('unexpected') or stats.get('skipped') or stats.get('flaky'):raise RuntimeError('Required launch browser acceptance did not pass: '+filename)
    if 'Compiled successfully' not in (OUT/'frontend-build.log').read_text() or (OUT/'frontend-types.log').read_text().strip():raise RuntimeError('Frontend build/types are not passing.')
    units=(OUT/'frontend-units-corrected.log').read_text()
    if '181 passed' not in units or 'failed' in units.lower():raise RuntimeError('Merged frontend unit acceptance is not passing.')
    recovery=json.loads((OUT/'recovery50/recovery-result.json').read_text())
    if not recovery.get('restored_exactly') or recovery.get('row_loss') or recovery.get('second_migration_run')!=0 or recovery.get('target_schema')!=50:raise RuntimeError('Current additive migration recovery did not pass.')
    if subprocess.check_output(['git','status','--porcelain','--','app','dashboard','scripts'],cwd=ROOT,text=True).strip():raise RuntimeError('Launch source must be committed before staging.')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()

def signed(client,path,method='GET',body=None):
    raw=json.dumps(body,separators=(',',':')).encode() if body is not None else b''
    values=dotenv_values(OPERATOR_ENV,interpolate=False);stamp=str(int(time.time()));nonce=secrets.token_hex(24);actor='planebyte@gmail.com'
    canonical='\n'.join((stamp,nonce,method,path,hashlib.sha256(raw).hexdigest(),actor))
    headers={'x-le-user':actor,'x-le-timestamp':stamp,'x-le-nonce':nonce,'x-le-signature':hmac.new(values['LEADENGINE_API_SIGNING_SECRET'].encode(),canonical.encode(),hashlib.sha256).hexdigest()}
    if raw:headers['content-type']='application/json'
    return client.request(method,path,headers=headers,content=raw)

def smoke(origin):
    checks={};paths={'/api/health':200,'/api/organization/products':200,'/api/organization/usage':200,'/api/organization/profile':200,'/api/organization/icps':200,'/api/intent-radar/overview':200,'/api/intent-radar/sources/health':200,'/api/intent-radar/alerts?alert_kind=Source%20issues':200,'/api/intent-radar/alerts?alert_kind=Monitor%20activity':200,'/api/intent-radar/assistant/conversations':200,'/api/intent-radar/growth/overview?days=0':200,'/api/organization/developer/status':200,'/api/workflow/safety':404,'/api/email/account':404,'/api/acquisition/providers':404}
    with httpx.Client(base_url=origin,timeout=65,follow_redirects=False) as client:
        if OUT.name=='final-remediation':paths['/api/intent-radar/overview/summary']=200
        for path,expected in paths.items():
            started=time.monotonic();r=client.get(path) if path=='/api/health' else signed(client,path)
            checks[path]={'http':r.status_code,'seconds':round(time.monotonic()-started,3),'server_timing':r.headers.get('server-timing','')}
            if r.status_code!=expected:raise RuntimeError('Read-only smoke failed at '+path+' (HTTP '+str(r.status_code)+').')
            if path.endswith('/products'):
                data=r.json()
                if data['lead_engine'] or data['lead_engine_available'] or not data['intent_radar']['enabled']:raise RuntimeError('Product availability policy mismatch.')
            if path.endswith('/usage'):
                data=r.json()
                if data['live_payments_enabled'] or data['commercial']['checkout_enabled'] or data['commercial']['catalog']['list_currency']!='USD':raise RuntimeError('Non-chargeable catalog policy mismatch.')
    return checks

def checkpoint(source):return ROOT/'data/backups'/('product-'+source[:10])

def stage():
    source=gate();build=json.loads((ROOT/'data/artifacts/verification/intent-only/build.json').read_text());remote=command(['builds','describe',build['build_id']])
    if build['source_commit']!=source or remote['status']!='SUCCESS' or remote['substitutions']['_SOURCE_REV']!=source:raise RuntimeError('Exact source images are not verified.')
    folder=checkpoint(source);folder.mkdir(mode=0o700,exist_ok=False)
    previous={name:command(['run',kind,'describe',name,'--region='+REGION]) for kind,name,_ in RESOURCES}
    for name,value in previous.items():save(folder/(name+'-before.json'),value)
    save(folder/'schedulers-before.json',command(['scheduler','jobs','list','--location='+REGION]))
    for kind,name,image in RESOURCES:
        before=copy.deepcopy(spec(previous[name],kind));env={e['name']:e for e in before['containers'][0].get('env',[])}
        for flag in ('AUTO_SCAN_ENABLED','AUTO_EMAIL_ENABLED','EMAIL_SENDING_ENABLED','HEYSOW_PUBLIC_REGISTRATION_ENABLED','BILLING_PUBLIC_CHECKOUT_ENABLED','LEAD_ENGINE_AVAILABLE'):
            if env.get(flag,{}).get('value')!='false':raise RuntimeError('A production safety flag is not explicitly false.')
        args=['run',kind,'update',name,'--region='+REGION,'--image='+build[image+'_image']]
        if kind=='services':args+=['--no-traffic','--tag=intent-only']
        updated=command(args);after=copy.deepcopy(spec(updated,kind))
        for runtime in (before,after):runtime['containers'][0].pop('image',None)
        if before!=after:raise RuntimeError('Unexpected runtime setting change; previous traffic remains unchanged.')
        save(folder/(name+'-staged.json'),updated)
        if kind=='services':
            revision=updated['status']['latestReadyRevisionName']
            if revision!=updated['status']['latestCreatedRevisionName']:raise RuntimeError('Staged API is not ready.')
            # Read smoke is complete before changing any worker image.
            save(folder/'staged-read-smoke.json',smoke('https://intent-only---leadengine-api-befca7xg4a-el.a.run.app'))
    from app.database.migrations import MIGRATIONS
    result={'source_commit':source,'revision':revision,'schema':46,'code_schema':len(MIGRATIONS),'migration_run':False,'production_traffic_promoted':False,'checkpoint':str(folder)}
    save(OUT/'staged-release.json',result);print(json.dumps(result))

def promote():
    source=gate();staged=json.loads((OUT/'staged-release.json').read_text());folder=checkpoint(source)
    if source!=staged['source_commit']:raise RuntimeError('Source changed after staging.')
    acceptance=json.loads((OUT/'staged-functional-acceptance.json').read_text())
    if acceptance.get('source_commit')!=source or acceptance.get('critical_failures') or not acceptance.get('worker_verified'):raise RuntimeError('Controlled staged worker acceptance is missing or failing.')
    revision=staged['revision'];original=json.loads((folder/'leadengine-api-before.json').read_text())
    checks=smoke('https://intent-only---leadengine-api-befca7xg4a-el.a.run.app')
    tags=sorted({row['tag'] for row in original['status']['traffic'] if row.get('tag')})
    command(['run','services','update-traffic','leadengine-api','--region='+REGION,'--to-revisions='+revision+'=100','--update-tags='+','.join(tag+'='+revision for tag in tags)])
    current=command(['run','services','describe','leadengine-api','--region='+REGION]);save(folder/'leadengine-api-final.json',current)
    if any(row.get('revisionName')!=revision for row in current['status']['traffic']):raise RuntimeError('Traffic/tag versions do not match the verified release.')
    before=json.loads((folder/'schedulers-before.json').read_text());after=command(['scheduler','jobs','list','--location='+REGION])
    clean=lambda rows:{r['name']:{k:v for k,v in r.items() if k not in ('lastAttemptTime','status','scheduleTime','userUpdateTime')} for r in rows}
    if clean(before)!=clean(after):raise RuntimeError('Scheduler settings changed concurrently.')
    proof={**staged,'production_traffic_promoted':True,'checks':checks,'schedulers_unchanged':True,'runtime_settings_preserved':True};save(OUT/'backend-promoted.json',proof);print(json.dumps(proof))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('stage','promote','smoke'));args=p.parse_args();os.umask(0o077)
    try:
        if args.action=='stage':stage()
        elif args.action=='promote':promote()
        else:save(OUT/'production-smoke.json',smoke(ORIGIN));print('Production read-only smoke passed.')
    except Exception as error:
        print(json.dumps({'status':'BLOCKED','error_type':type(error).__name__,'detail':str(error) if isinstance(error,RuntimeError) else 'Inspect the private checkpoint; credentials withheld.'}));raise SystemExit(1)
