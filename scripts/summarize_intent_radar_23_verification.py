"""Read-only compact export of final local verification artifacts and source hashes."""
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

root=Path(__file__).resolve().parents[1]
evidence=root/'data/artifacts/verification'
def load(name):return json.loads((evidence/name).read_text())
def xml(name):
    suite=ET.parse(evidence/name).getroot().find('testsuite')
    return {key:int(suite.attrib[key]) for key in ('tests','failures','errors','skipped')}
sources=load('intent-radar23-live-sources-final.json')
quality=load('intent-radar23-ai-quality-final.json')
inspection=load('intent-radar23-inspection-final.json')
checks=[]
for report in sources['reports']:
    runs=report['source_runs']
    checks.append({'sources':report['sources'],'hn_feeds':report['feeds'],'job_status':report['job_status'],
        'submission_ms':report['submission_ms'],'completion_seconds':report['completion_seconds'],
        'runs':[{k:r.get(k) for k in ('provider','status','requests','scanned','quota_remaining','errors')} for r in runs]})
hashes={}
paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=root).decode().split('\0')
for name in sorted(set(paths)-{''}):
    path=Path(name)
    if any(p.startswith(('.next','.env','__pycache__')) or p in {'node_modules','artifacts'} for p in path.parts):continue
    if path.suffix not in {'.py','.ts','.tsx','.css','.mjs','.cjs','.json','.md','.toml'}:continue
    if (root/path).is_file():hashes[name]=hashlib.sha256((root/path).read_bytes()).hexdigest()
browser={}
for name in ('browser-final','radar-final','lead-engine-final','gmail-final','live-browser-final','platform-auth-repaired','platform-workspace','platform-workspace-final','platform-integrations','platform-ui','platform-ui-repaired'):
    content=(evidence/('intent-radar23-'+name+'.log')).read_text()
    browser[name]={key:int(matches[-1]) if (matches:=re.findall(r'\b(\d+) '+key+r'\b',content)) else 0 for key in ('passed','failed','skipped')}
analyses=[a for row in inspection['analyses'] for a in row['valid_analyses']]
frontend=(evidence/'intent-radar23-frontend-repaired.log').read_text()
result={'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip(),
 'backend':xml('intent-radar23-backend-frozen.xml'),'postgres':xml('intent-radar23-postgres-final.xml'),
 'frontend_units':int(re.findall(r'Tests\s+(\d+) passed',frontend)[-1]),
 'typecheck':'PASS' if (evidence/'intent-radar23-types-frozen.log').read_text().strip()=='> leadengine-dashboard@3.0.0 typecheck\n> tsc --noEmit' else 'REVIEW_LOG',
 'production_build':'PASS' if 'Compiled successfully' in (evidence/'intent-radar23-build-final.log').read_text() and 'Generating static pages' in (evidence/'intent-radar23-build-final.log').read_text() else 'REVIEW_LOG',
 'browser':browser,'source_checks':checks,'initial_unique_signals_by_source':dict(Counter(s['source'] for s in sources['samples'])),
 'quality':{k:quality[k] for k in ('version','status','provider','model','sample_size','accuracy','evidence_attribution','false_positives','high_score_false_positives')},
 'evaluation_scores':{s['id']:s['scoring']['overall'] for s in quality['scoring']},
 'live_analyses':[{'provider':a['provider'],'model':a['model'],'categories':a['interpretation']['categories'],'icp':a['icp'],'score':a['scoring']['overall'],'expressed_need':a['scoring']['dimensions']['expressed_need']} for a in analyses],
 'lead_engine_and_mail_counts':inspection['lead_engine_and_mail_counts'],'performance':inspection['performance'],
 'source_sha256':hashes}
print(json.dumps(result,indent=2))
