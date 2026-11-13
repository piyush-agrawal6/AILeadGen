"""Read-only resume inventory. Never emits environment or credential values."""
import argparse
import json
import textwrap
from pathlib import Path
from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--requirements',nargs='*')
parser.add_argument('--state-summary',action='store_true')
parser.add_argument('--line',help='Print a source line wrapped for precise patch review: relative-path:line')
args=parser.parse_args()
if args.state_summary:
    from collections import Counter
    rows=json.loads((ROOT/'docs/INTENT_RADAR_PHASE_2_3_REQUIREMENTS_AUDIT.json').read_text())
    assert len(rows)==510 and len({row['id'] for row in rows})==510
    print(json.dumps({'requirements':510,'status_counts':dict(Counter(row['status'] for row in rows)),'current_release_verified':[row['id'] for row in rows if row['status']=='VERIFIED' and row.get('release_evidence')],'outstanding':{status:[row['id'] for row in rows if row['status']==status] for status in sorted({row['status'] for row in rows}-{'VERIFIED','NOT APPLICABLE'})}},indent=2))
elif args.line:
    name,line=args.line.rsplit(':',1)
    path=(ROOT/name).resolve()
    if not path.is_relative_to(ROOT) or any(p.startswith('.env') for p in path.parts):raise ValueError('Application source only.')
    print('\n'.join(textwrap.wrap(path.read_text().splitlines()[int(line)-1],width=140,break_long_words=False,break_on_hyphens=False)))
elif args.requirements is not None:
    rows=json.loads((ROOT/'docs/INTENT_RADAR_PHASE_2_3_REQUIREMENTS_AUDIT.json').read_text())
    for row in rows:
        if args.requirements and not any(row['id'].startswith(prefix) for prefix in args.requirements):continue
        if row['status'] in ('VERIFIED','NOT APPLICABLE'):continue
        print(json.dumps({k:v for k,v in row.items() if k in ('id','expected','requirement','status','expected_behavior')},ensure_ascii=False))
else:
    variables=['INTENT_RADAR_STAGE','INTENT_RADAR_INTERNAL_WORKSPACES','INTENT_RADAR_STACKEXCHANGE_ENABLED','INTENT_RADAR_STACKEXCHANGE_KEY','INTENT_RADAR_STACKEXCHANGE_SITES','INTENT_RADAR_APPROVED_FEED_HOSTS','INTENT_RADAR_SCHEDULES_ENABLED','INTENT_RADAR_MIN_SCHEDULE_HOURS','INTENT_RADAR_AI_ENABLED','INTENT_RADAR_AI_DAILY_CALLS','INTENT_RADAR_AI_DAILY_TOKENS','HEYSOW_DEVELOPER_API_ENABLED','HEYSOW_MCP_ENABLED','MCP_ALLOWED_HOSTS','MCP_ALLOWED_ORIGINS','AI_PRIMARY_PROVIDER','VERTEX_AI_ENABLED','VERTEX_AI_PROJECT_ID','VERTEX_AI_LOCATION','VERTEX_AI_MODEL','GEMINI_API_ENABLED','AI_FALLBACK_ENABLED','GEMINI_API_KEY','GEMINI_MODEL','AUTH_SECRET','AUTH_URL','AUTH_GOOGLE_ID','AUTH_GOOGLE_SECRET','LEADENGINE_API_SIGNING_SECRET','LEADENGINE_API_URL','DATABASE_BACKEND','DATABASE_URL','ALLOWED_USER_EMAILS','HEYSOW_INTEGRATION_ENCRYPTION_KEY','AI_MODEL_PRICING_JSON']
    files={name:dotenv_values(ROOT/name,interpolate=False) for name in ('.env','dashboard/.env','dashboard/.env.local') if (ROOT/name).is_file()}
    print(json.dumps({key:{name:bool(values.get(key)) for name,values in files.items()} for key in variables},indent=2))
