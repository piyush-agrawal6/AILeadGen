"""Validate audit traceability and current additive evidence, without provider calls."""
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'data/artifacts/verification'
rows=json.loads((ROOT/'docs/INTENT_RADAR_PHASE_2_3_REQUIREMENTS_AUDIT.json').read_text())
allowed={'VERIFIED','IMPLEMENTED BUT NOT VERIFIED','PARTIALLY IMPLEMENTED','MISSING','BROKEN','BLOCKED BY EXTERNAL APPROVAL','NOT APPLICABLE'}
fields={'id','expected','actual','backend','frontend','api','database','existing','verification','live','status','root_cause','remediation','blocker','priority','local_complete'}
assert len(rows)==510 and len({r['id'] for r in rows})==510
for row in rows:
    assert fields<=row.keys() and row['status'] in allowed
    assert all(row[key] for key in fields-{'local_complete'})
    assert 'pending assessment' not in row['actual'].lower() and 'not yet performed' not in row['verification'].lower()
for name in ['INTENT_RADAR_PHASE_2_3_REQUIREMENTS_AUDIT.md','INTENT_RADAR_PHASE_2_3_COMPLETE_FUNCTIONAL_AUDIT.md','INTENT_RADAR_PHASE_2_3_UI_ACCEPTANCE.md','INTENT_RADAR_PHASE_2_3_FINAL_READINESS.md','PLANEBYTE_REQUIRED_CREDENTIALS_AND_LAUNCH_SETUP.md','PLANEBYTE_LAUNCH_SETUP_VARIABLES.md']:
    assert (ROOT/'docs'/name).is_file()

def junit(name):
    cases=ET.parse(EVIDENCE/name).getroot().findall('.//testcase')
    failed=sum(c.find('failure') is not None or c.find('error') is not None for c in cases)
    skipped=sum(c.find('skipped') is not None for c in cases)
    return {'total':len(cases),'passed':len(cases)-failed-skipped,'failed_or_error':failed,'skipped':skipped}
backend=junit('intent-radar23-product-backend-closure.xml')
postgres=junit('intent-radar23-product-postgres-recovery.xml')
assert backend['passed']==822 and backend['failed_or_error']==0
assert postgres['passed']==56 and postgres['failed_or_error']==0

suites={'product':'pages','phase23':'recovery','radar':'final','lead-engine':'final','gmail':'final','platform':'final','platform-workspace':'final','platform-integrations':'final','developer':'final','live':'final'}
identities=set();browser_counts={};browser_evidence=[]
for suite,label in suites.items():
    path=EVIDENCE/f'intent-radar23-product-{suite}-{label}-results.json'
    data=json.loads(path.read_text());count=[0]
    def walk(nodes,parents=()):
        for node in nodes:
            current=parents+(node.get('title',''),)
            for spec in node.get('specs',[]):
                for test in spec.get('tests',[]):
                    assert any(r['status']=='passed' for r in test['results']) and test['status']=='expected', (path,spec['title'])
                identities.add((spec.get('file',node.get('file','')),current+(spec['title'],)))
                count[0]+=1
            walk(node.get('suites',[]),current)
    walk(data['suites']);browser_counts[suite]=count[0]
    browser_evidence.append(str(path.relative_to(ROOT)))
assert len(identities)==61, (len(identities),browser_counts)
quality=json.loads((EVIDENCE/'intent-radar23-product-live-ai-final.log').read_text())
assert quality['status']=='QUALITY_GATE_FAILED' and quality['accuracy']==.875 and quality['independent_adjudication'] is False
variables=json.loads((ROOT/'docs/PLANEBYTE_LAUNCH_SETUP_VARIABLES.json').read_text())
assert len(variables)==132 and all('value' not in row and isinstance(row['configured_presence_only'],bool) for row in variables)
for file in ['intent-radar23-product-build-routes.json','intent-radar23-product-types-closure.json','intent-radar23-product-units-final.json']:
    record=json.loads((EVIDENCE/file).read_text());assert record['returncode']==0 and record['node']=='24.22.2'
summary={'requirements':len(rows),'requirement_statuses':dict(Counter(r['status'] for r in rows)),
    'backend':backend,'postgres':postgres,'browser_distinct_scenarios':len(identities),'browser_suite_counts':browser_counts,
    'browser_evidence':browser_evidence,'node':'24.22.2','quality_status':quality['status'],'quality_accuracy':quality['accuracy'],
    'configuration_contracts':len(variables),'secret_values_recorded':False,'launch':'NO-GO'}
initial=Path('/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/intent-radar-23-product-audit-20261111')
with zipfile.ZipFile(initial/'source.zip') as archive:
    summary['initial_branch_status']=archive.read('CHECKPOINT/status.txt').decode().splitlines()[0]
(EVIDENCE/'intent-radar23-product-evidence-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
