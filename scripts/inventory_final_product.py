"""Reproducible static product surface inventory; not a functional certification.

Requirement rows begin PARTIAL until individually reconciled. Source controls
are IMPLEMENTED / NOT VERIFIED solely as code surfaces, never working journeys.
"""
import ast,collections,hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STARTING_COMMIT='e8ff078dc356653873d2f26de4d0563dd3ff7096'
BRIEF=Path('/Users/planebyte/.codex/attachments/2c6f655a-21c7-4a75-9a45-332c1bee2cf4/Pasted text.txt')
STATUSES=['VERIFIED LIVE','IMPLEMENTED / NOT VERIFIED','BROKEN','PARTIAL','MISSING','EXTERNALLY BLOCKED','INTENTIONALLY HIDDEN','NOT APPLICABLE']
GROUPS={
'A':('Authentication and accounts','/login; /account','dashboard/components/auth','app/platform/admission.py'),
'B':('Workspaces and teams','/settings','dashboard/components/workspaces','app/api/organization.py'),
'C':('Onboarding','/onboarding','dashboard/components/workspaces','app/platform/onboarding.py'),
'D':('Shell and usability','Global shell','dashboard/components/layout','app/api/security.py'),
'E':('Discovery','/intent-radar/discover','dashboard/components/intent-radar/discovery.tsx','app/intent_radar/discovery.py'),
'F':('Sources','/intent-radar/integrations','dashboard/components/intent-radar/source-management.tsx','app/intent_radar/connectors.py'),
'G':('Signals','/intent-radar/signals','dashboard/components/intent-radar/signal-workspace.tsx','app/intent_radar/intelligence.py'),
'H':('Opportunities','/intent-radar/opportunities','dashboard/components/intent-radar/research-experience.tsx','app/intent_radar/service.py'),
'I':('Monitoring','/intent-radar/monitors','dashboard/components/intent-radar/monitor-experience.tsx','app/intent_radar/schedules.py'),
'J':('Growth Intelligence','/intent-radar/growth','dashboard/components/intent-radar/growth-experience.tsx','app/growth_intelligence/service.py'),
'K':('AI assistant','Global assistant','dashboard/components/intent-radar/assistant-panel.tsx','app/intent_radar/assistant.py'),
'L':('Library','/intent-radar/saved','dashboard/components/intent-radar/research-experience.tsx','app/intent_radar/service.py'),
'M':('Alerts','/intent-radar/alerts','dashboard/components/intent-radar/research-experience.tsx','app/intent_radar/service.py'),
'N':('Connections and MCP','/intent-radar/integrations; /settings/developer','dashboard/components/intent-radar/integrations.tsx','app/developer/mcp_server.py'),
'O':('Billing','/billing','dashboard/components/workspaces/usage.tsx','app/billing/service.py'),
'P':('Usage','/billing','dashboard/components/workspaces/usage.tsx','app/billing/commercial_usage.py'),
'Q':('Performance','All product pages','dashboard/lib/intent-radar.ts','app/database/postgres.py'),
'R':('Security and operations','All protected resources','dashboard/auth.ts','app/api/security.py'),
'S':('Release acceptance','Production customer journeys','dashboard/intent-radar23-e2e','scripts/deploy_product_release.py')}

def row(key,title,location,frontend,backend,*,kind='requirement',status='PARTIAL',line=None):
 return dict(id=key,feature=title,kind=kind,user_location=location,frontend=frontend,backend=backend,line=line,database_workers=[],status=status,reason='Area implementation exists; this specific requirement needs individual source and authenticated live reconciliation. No completion inferred from a page or test file.',severity='P1',user_impact='Customer journey acceptance is not established.',remediation='Inspect actual implementation, reproduce the action and record precise acceptance evidence.',tests_evidence=[],deployment_verification=[],remaining_owner_action=None)

def main():
 records=[];section=None;sequence=collections.Counter();in_checklist=False
 for line in BRIEF.read_text().splitlines():
  if line.startswith('# PART 14'):in_checklist=True
  if line.startswith('# PART 15'):in_checklist=False
  found=re.match(r'## ([A-S])\. ',line)
  if in_checklist and found:section=found[1]
  if in_checklist and section and line.startswith('- [ ] '):
   sequence[section]+=1;group,location,frontend,backend=GROUPS[section]
   records.append(row(f'{section}.{sequence[section]:02}',line[6:].strip().rstrip('.'),location,frontend,backend))
 # Known reproducible defects and genuine external dependencies override initial status.
 for r in records:
  title=r['feature'].casefold()
  if r['id'].startswith('Q.') and title in ('fast overview','fast opportunities','fast growth intelligence','fast billing page','fast settings','fast signal list'):
   r.update(status='BROKEN',severity='P0',reason='Production authenticated reads remain 8–21s; small post-release samples are recorded, not an SLA.',tests_evidence=['data/artifacts/verification/final-product/production-after.json'],remediation='Reduce serial SQL/auth/session round trips; add summary reads and measure realistic concurrency.')
  if r['id'].startswith('K.') and title in ('accurate workspace counts','accurate quota answers','safe tool routing'):
   r.update(status='PARTIAL',severity='P0',reason='Production defect reproduced. New deterministic authorized read router passes isolated backend and browser checks; exact deployed acceptance remains required.',backend='app/intent_radar/assistant_reads.py',tests_evidence=['tests/unit/test_assistant_workspace_reads.py','tests/integration/test_growth_postgres.py','dashboard/intent-radar23-e2e/product-overhaul.spec.ts'],remediation='Complete matching-release production acceptance without AI quota consumption.')
  if r['id'].startswith('H.') and title=='qualification criteria':
   r.update(status='PARTIAL',severity='P0',reason='New evidence-admission policy blocks topic-only and negative/noncommercial promotion locally. Historical records are preserved. Deployed acceptance and independent quality review are separate.',tests_evidence=['tests/unit/test_opportunity_evidence_policy.py'],remediation='Accept on actual deployed evidence; evaluate non-English and independent quality coverage before broad claims.')
  if ('human evaluation' in title or title in ('payu recurring capabilities','stack exchange permission evidence','discourse publisher terms','rss publisher terms')):
   r.update(status='EXTERNALLY BLOCKED',reason='Independent reviewers or merchant/publisher-specific approval is not supplied; existing code does not establish permission.',remaining_owner_action='Provide the applicable reviewer assignment or provider/publisher confirmation; never send secrets in chat.')
 # Every backend route, including hidden legacy routes, is recorded with exact source line.
 from app.platform.modules import lead_engine_route
 for path in sorted((ROOT/'app/api/routes').glob('*.py')):
  tree=ast.parse(path.read_text());prefix=''
  for node in ast.walk(tree):
   if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='APIRouter':
    prefix=next((kw.value.value for kw in node.keywords if kw.arg=='prefix' and isinstance(kw.value,ast.Constant)),'')
  for node in tree.body:
   if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):continue
   for d in node.decorator_list:
    if not isinstance(d,ast.Call) or not isinstance(d.func,ast.Attribute) or d.func.attr not in ('get','post','put','patch','delete') or not d.args or not isinstance(d.args[0],ast.Constant):continue
    route='/api'+prefix+str(d.args[0].value)
    if route.startswith('/api/api/'):route=route[4:]
    hidden=lead_engine_route(route) or route.startswith('/api/v1/') and not route.startswith('/api/v1/intent-radar/') and route!='/api/v1/mcp'
    r=row('API.'+path.stem+'.'+node.name,d.func.attr.upper()+' '+route,route,'',str(path.relative_to(ROOT)),kind='endpoint',line=node.lineno,status='INTENTIONALLY HIDDEN' if hidden else 'IMPLEMENTED / NOT VERIFIED')
    r['reason']='Preserved Lead Engine endpoint; server availability gate denies ordinary launch users.' if hidden else 'Exact decorated handler exists; direct and workflow acceptance must be verified separately.'
    records.append(r)
 # Page implementations and all explicit/dynamic product routes.
 lead_source=(ROOT/'dashboard/lib/product-availability.ts').read_text()
 lead_pages=re.findall(r"'([^']+)'",lead_source.split('const leadPages=')[1].split('];')[0])
 for path in sorted((ROOT/'dashboard/app').rglob('page.tsx')):
  rel=path.relative_to(ROOT/'dashboard/app');route='/'+str(rel.parent)
  if route=='/.':route='/'
  hidden=any(route==p or route.startswith(p+'/') for p in lead_pages)
  r=row('PAGE.'+str(rel.parent).replace('/','.'),route,route,str(path.relative_to(ROOT)),'',kind='page',status='INTENTIONALLY HIDDEN' if hidden else 'IMPLEMENTED / NOT VERIFIED');r['reason']='Preserved legacy page behind reversible server availability gates.' if hidden else 'Page implementation exists; this is not evidence that its controls work or that access is enabled.';records.append(r)
 # Expand the real catch-all allowlist rather than counting it as one feature.
 radar_page=ROOT/'dashboard/app/intent-radar/[[...segments]]/page.tsx'
 declared=re.search(r'const routes=\[(.*?)\]',radar_page.read_text()).group(1)
 for route in [*re.findall(r"'([^']*)'",declared),*[p+'/{uuid}' for p in ('monitors','signals','opportunities','growth/themes','growth/research')]]:
  full='/intent-radar'+('/'+route if route else '')
  records.append(row('RADAR_PAGE.'+(route.replace('/','.') or 'overview'),full,full,str(radar_page.relative_to(ROOT)),'app/api/routes/intent_radar.py',kind='product_route',status='IMPLEMENTED / NOT VERIFIED'))
 for path in sorted((ROOT/'dashboard/components').rglob('*.tsx')):
  text=path.read_text();rel=str(path.relative_to(ROOT))
  r=row('COMPONENT.'+str(path.relative_to(ROOT/'dashboard/components')).replace('/','.'),path.stem,'Component-dependent',rel,'',kind='component',status='IMPLEMENTED / NOT VERIFIED');records.append(r)
  for n,match in enumerate(re.finditer(r'<(button|Button|form|Dialog|Select|input|textarea|DropdownMenuItem)\b',text),1):
   line=text[:match.start()].count('\n')+1
   records.append(row(f'CONTROL.{rel}.{n}',match.group(1),f'{rel}:{line}',rel,'',kind='control',status='IMPLEMENTED / NOT VERIFIED',line=line))
 # Persisted intelligence kinds and operator/worker entry points are separate
 # surfaces, never inferred from the presence of a frontend page.
 from app.intelligence.jobs import Start
 from typing import get_args
 for kind in get_args(Start.model_fields['kind'].annotation):
  hidden=kind not in ('INTENT_DISCOVER','GROWTH_ANALYZE')
  r=row('JOB.'+kind,kind,'Background jobs','','app/intelligence/jobs.py',kind='job',status='INTENTIONALLY HIDDEN' if hidden else 'IMPLEMENTED / NOT VERIFIED')
  r['database_workers']=['intelligence_jobs','intelligence_job_items','app/worker.py','app/intelligence/dispatch.py'];records.append(r)
 for rel in ('app/worker.py','app/acquisition/worker.py','app/acquisition/dispatch.py','app/intelligence/dispatch.py','app/intent_radar/schedules.py','app/platform/company_discovery_dispatch.py','app/webhooks/dispatch.py','app/webhooks/worker.py'):
  records.append(row('WORKER.'+rel,rel,'Operator / background execution','',rel,kind='worker',status='IMPLEMENTED / NOT VERIFIED'))
 from app.config.settings import Settings
 for name in Settings.model_fields:
  r=row('CONFIG.'+name,name,'Server configuration','','app/config/settings.py',kind='configuration',status='IMPLEMENTED / NOT VERIFIED')
  r['reason']='Server setting definition exists. No secret values or inferred runtime readiness are included.';records.append(r)
 for key,name in [('hacker_news','Official Hacker News'),('stack_exchange','Official Stack Exchange'),('rss','Approved RSS/Atom'),('discourse','Approved Discourse feeds')]:
  external=key!='hacker_news'
  r=row('SOURCE.'+key,name,'/intent-radar/integrations','dashboard/components/intent-radar/source-management.tsx','app/intent_radar/connectors.py',kind='source',status='EXTERNALLY BLOCKED' if external else 'IMPLEMENTED / NOT VERIFIED')
  r['database_workers']=['intent_source_configs','intent_source_cache','intent_source_runs','intent_source_usage']
  r['reason']='Applicable publisher permission/endpoint approval remains required; adapter code does not establish permission.' if external else 'Bounded official adapter exists; current live collection is verified separately.'
  records.append(r)
 overrides=ROOT/'docs/FINAL_PRODUCT_AUDIT_OVERRIDES.json'
 if overrides.exists():
  values=json.loads(overrides.read_text())
  for r in records:
   if r['id'] in values:
    r.update(values[r['id']])
    if r['status'] not in STATUSES:raise ValueError('Unknown audit status.')
 docs={}
 for path in sorted((ROOT/'docs').glob('*')):
  if path.suffix=='.md' and re.search('INTENT_RADAR|GROWTH|BILLING|PAYU|PERFORMANCE|SECURITY|READINESS|DEPLOYMENT',path.name):
   text=path.read_text();docs[str(path.relative_to(ROOT))]={'sha256':hashlib.sha256(text.encode()).hexdigest(),'lines':len(text.splitlines()),'historical_claim_lines':[line[:250] for line in text.splitlines() if re.search(r'NO.GO|pending|blocked|not yet|[0-9]+ passed|NOT PERFORMED',line,re.I)][:12]}
 counts=dict(collections.Counter(r['status'] for r in records));kinds=dict(collections.Counter(r['kind'] for r in records))
 data={'audit_version':2,'starting_commit':STARTING_COMMIT,'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'phase':'Source reconciliation and current acceptance; open rows remain explicit','claim_policy':'No inherited completion percentages or historical VERIFIED labels become VERIFIED LIVE. Static elements are code surfaces only, not functional acceptance. PARTIAL requirement rows explicitly remain unassessed at subfeature level.','status_values':STATUSES,'counts':{s:counts.get(s,0) for s in STATUSES},'surface_counts':kinds,'features':records,'reviewed_report_index':docs}
 (ROOT/'docs/FINAL_PRODUCT_FEATURE_INVENTORY.json').write_text(json.dumps(data,indent=2)+'\n')
 lines=['# Final product feature inventory','',data['phase'],'',data['claim_policy'],'','Starting commit: `'+data['starting_commit']+'`','',f'Exact inventory denominator: **{len(records)} records**. Mandatory requirement rows and static technical surfaces are separate kinds; do not count them as unique completed customer capabilities.','', '| Status | Records |','|---|---:|']+[f'| {s} | {counts.get(s,0)} |' for s in STATUSES]
 lines+=['','All required metadata, source locations and provisional reasons are in the JSON. Regex control enumeration is a discovery aid, not a complete JSX/dataflow proof. Dynamic routes and handler links still need reconciliation.','', '| ID | Requirement | Initial status | Source |','|---|---|---|---|']
 lines += [f"| {r['id']} | {r['feature']} | {r['status']} | {r['backend']} |" for r in records if r['kind']=='requirement']
 (ROOT/'docs/FINAL_PRODUCT_FEATURE_INVENTORY.md').write_text('\n'.join(lines)+'\n')
 print(json.dumps({'records':len(records),'counts':data['counts'],'surfaces':kinds,'report_files':len(docs)}))
if __name__=='__main__':main()
