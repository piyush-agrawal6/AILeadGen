"""Inventory actual configuration names and presence; never output values."""
import ast
import json
import os
import re
from pathlib import Path

from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parents[1]
contracts={}
for relative in ['app/config/settings.py','app/acquisition/config.py']:
    tree=ast.parse((ROOT/relative).read_text())
    for cls in [n for n in tree.body if isinstance(n,ast.ClassDef) and any(isinstance(b,ast.Name) and b.id=='BaseSettings' for b in n.bases)]:
        for node in cls.body:
            if not isinstance(node,ast.AnnAssign) or not isinstance(node.target,ast.Name):continue
            call=node.value if isinstance(node.value,ast.Call) else None
            alias=next((kw.value for kw in call.keywords if kw.arg in ('validation_alias','alias')),None) if call else None
            name=alias.value if isinstance(alias,ast.Constant) and isinstance(alias.value,str) else node.target.id.upper()
            required=node.value is None or bool(call and call.args and isinstance(call.args[0],ast.Constant) and call.args[0].value is Ellipsis)
            contracts.setdefault(name,{'references':[],'required_by_settings':False})
            contracts[name]['references'].append(f'{relative}:{node.lineno}')
            contracts[name]['required_by_settings']|=required
for relative in ['dashboard/lib/server/env.ts','dashboard/auth.ts','app/database/connection.py','app/acquisition/vertex.py']:
    text=(ROOT/relative).read_text()
    names=set(re.findall(r'(?:process\.env\.|os\.environ\[\s*[\'\"]|os\.environ\.get\(\s*[\'\"]|os\.getenv\(\s*[\'\"])([A-Z][A-Z0-9_]+)',text))
    if relative.endswith('env.ts'):names.update(re.findall(r'[\'\"]([A-Z][A-Z0-9_]+)[\'\"]',text))
    for name in names:
        contracts.setdefault(name,{'references':[],'required_by_settings':False})['references'].append(relative)
frontend_required=set(re.findall(r'\"([A-Z][A-Z0-9_]+)\"',re.search(r'const required = \[(.*?)\]',(ROOT/'dashboard/lib/server/env.ts').read_text()).group(1)))
files={str(p.relative_to(ROOT)):dotenv_values(p,interpolate=False) for p in [ROOT/'.env',ROOT/'dashboard/.env',ROOT/'dashboard/.env.local'] if p.is_file()}

def setup(name):
    if name.startswith(('AUTH_GOOGLE','GOOGLE_CLIENT')):
        return ('Google OAuth','Google Cloud Console → APIs & Services → Credentials; existing approved web client','Auth.js `/api/auth/callback/google`; customer integrations have separate persisted state and callbacks','Approved Google sign-in / customer OAuth')
    if name.startswith('AUTH_') or name in ('ALLOWED_USER_EMAILS','LEADENGINE_API_SIGNING_SECRET','LEADENGINE_API_URL'):
        return ('Shared authentication/gateway','Owner-managed canonical origins, approved account list and secret manager','Existing signed gateway and session flow; public signup remains gated','Secure sessions and backend proxy')
    if name.startswith(('VERTEX','AI_PRIMARY','AI_FALLBACK','AI_PROVIDER')) or name=='GOOGLE_APPLICATION_CREDENTIALS':
        return ('Existing Vertex/Gemini gateway','Approved Google Cloud Vertex project and attached production identity; local approved ADC; API/billing/IAM acceptance','No OAuth callback; Vertex inference permission. Production forbids credential-file authentication','Structured AI drafts and Radar analyses')
    if name.startswith('GEMINI'):
        return ('Approved Gemini fallback','Approved Google AI Studio API key and model/quota policy','No OAuth callback; fallback approval and existing router bounds','Optional approved fallback AI')
    if 'GMAIL' in name or 'CUSTOMER_MAIL' in name or 'INTEGRATION_ENCRYPTION' in name:
        return ('Preserved Gmail B04 / customer integrations','Existing owner OAuth application and secret manager; mailbox owner gives consent; platform sending approval separate','Gmail frontend callback `/settings/integrations/gmail-callback`; `openid email gmail.send gmail.readonly` as requested by implementation. No audit send authorization','Customer Gmail connection / protected mail operations')
    if name.startswith(('MAIL_','SMTP','EMAIL_','HOSTINGER','SENDER','IMAP','AUTO_EMAIL')):
        return ('Existing mail/provider settings','Existing owner mail provider account; preserve disabled sending and explicit approval gates','Provider authentication; no real mail acceptance authorized by this audit','Legacy/approved mail functionality when explicitly activated')
    if name.startswith('INTENT_RADAR_'):
        return ('Intent Radar policy/budgets','Owner-approved module entitlement, allowed public hosts/sites and source terms; use existing admin configuration','No source-account OAuth implemented. Stack Exchange key optional; publisher/instance commercial approval required','Radar sources, optional AI and opt-in recurring monitoring')
    if name.startswith(('HEYSOW_MCP','MCP_','HEYSOW_DEVELOPER','DEVELOPER_','HEYSOW_WEBHOOK')):
        return ('Developer API / MCP / webhook policy','Owner/admin scoped expiring workspace keys and approved HTTPS endpoints; use existing developer settings','MCP requires `mcp:use` plus appropriate read scope and active issuing membership','Approved developer access / automation')
    if name.startswith('R2_'):
        return ('Existing Cloudflare R2','Existing scoped private bucket credentials from owner Cloudflare account','Private storage access; no OAuth callback','Stored attachments and reports')
    if name.startswith('UPSTASH_'):
        return ('Existing optional Upstash cache','Existing scoped REST credentials from owner Upstash console','No OAuth callback; workspace/actor cache keys retained','Optional cache, not primary authorization or persistence')
    if name.startswith(('DATABASE_','DB_')):
        return ('Existing SQLite/PostgreSQL','Existing owner database role/service; isolated test schemas only in audit','No OAuth callback; approved additive migrations and recovery acceptance','Durable SaaS state')
    if name.startswith(('GOOGLE_MAPS','MAPS_','PLACES_')):
        return ('Existing Google Maps acquisition','Owner Google Cloud API console; approved API, restricted key and billing/quota','Maps/Places API restrictions and commercial policy','Lead Engine approved discovery sources')
    if name.startswith('FIRECRAWL_'):
        return ('Existing optional Firecrawl','Owner Firecrawl dashboard; existing API key and bounded paid-provider approval','No OAuth callback; operator-approved acquisition only','Optional approved Lead Engine crawling')
    if name.startswith(('GOOGLE_SHEETS','SHEETS_')):
        return ('Existing Sheets integration','Existing owner Google OAuth web client and user consent','Read-only Sheets OAuth import; explicit workspace state/permissions required','Approved customer Sheets import/export contract')
    if name.startswith(('GCP_','SCAN_EXECUTOR','LEADENGINE_CLOUD_RUN','ACQUISITION_CLOUD_RUN')):
        return ('Existing Google Cloud workers','Existing owner project/region/job and attached service identity','Approved job invocation/IAM; no new infrastructure','Authorized durable background dispatch')
    return ('Application policy/optional platform setting','Owner-controlled existing application configuration; this name does not imply a third-party credential','Follow exact referenced feature gate/validation; no new account or paid service inferred','Corresponding referenced optional/shared platform behavior')

rows=[]
for name,contract in sorted(contracts.items()):
    service,obtain,approval,feature=setup(name)
    locations=[]
    if any(ref.startswith('dashboard/') for ref in contract['references']):locations.append('Frontend server')
    if any(ref.startswith('app/') for ref in contract['references']):locations.append('Backend/worker')
    required='Required by settings constructor' if contract['required_by_settings'] else 'Optional/defaulted; conditionally required when its feature is enabled (exact validator in source)'
    if name in frontend_required:required='Required by frontend server production validator; backend also requires matching configuration where referenced'
    if name=='GOOGLE_APPLICATION_CREDENTIALS':required='Forbidden in production; optional local ADC file selector. Managed/local ADC discovery can work without this variable.'
    rows.append({'name':name,'service':service,'location':'; '.join(locations),'requiredness':required,
        'configured_presence_only':bool(os.environ.get(name)) or any(bool(v.get(name)) for v in files.values()),
        'files_with_nonempty_value':[file for file,values in files.items() if values.get(name)],
        'process_presence':bool(os.environ.get(name)),'source':contract['references'],
        'owner_obtains':obtain,'callbacks_scopes_approvals':approval,'blocked_feature':feature,
        'apply':'Restart backend/worker/frontend server that reads it; frontend public build-time flags require rebuild; deployed changes require separately authorized rollout.'})
(ROOT/'docs/PLANEBYTE_LAUNCH_SETUP_VARIABLES.json').write_text(json.dumps(rows,indent=2)+'\n')
lines=['# Complete actual launch-variable inventory','',
 'Generated from actual settings aliases and server environment reads. Values are never recorded. Presence checks inspect local `.env`, `dashboard/.env`, `dashboard/.env.local` and this audit process; they cannot attest to deployed secret configuration. Defaults are not explicit presence. Non-empty `false` is present but disabled. No missing variable is automatically a missing credential.', '',
 'The source reference is the precise name/validation contract. Curated service instructions and owner launch gates are in `PLANEBYTE_REQUIRED_CREDENTIALS_AND_LAUNCH_SETUP.md`. Variables are server-only unless the reference explicitly reads a public build-time switch. Secrets belong in existing local files or the approved secret manager, never chat/source/logs.', '',
 '| Actual variable | Service / location / requiredness | Presence | Exact source | Owner obtains / callbacks, scopes, approvals | Blocked feature / apply |','|---|---|---|---|---|---|']
for row in rows:
    lines.append('| '+ ' | '.join([f"`{row['name']}`",f"{row['service']}<br>{row['location']}<br>{row['requiredness']}",
        'Present (values not inspected for acceptance)' if row['configured_presence_only'] else 'Absent explicitly; defaults/managed identity may apply',
        '<br>'.join('`'+ref+'`' for ref in row['source']),
        row['owner_obtains']+'<br>'+row['callbacks_scopes_approvals'],row['blocked_feature']+'<br>'+row['apply']])+' |')
(ROOT/'docs/PLANEBYTE_LAUNCH_SETUP_VARIABLES.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'variables':len(rows),'explicitly_present':sum(r['configured_presence_only'] for r in rows),'explicitly_absent':sum(not r['configured_presence_only'] for r in rows),'values_recorded':False},indent=2))
