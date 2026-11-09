"""Workspace administrator approval separates model/tool intent from user authority."""
import hashlib,json,uuid
from datetime import datetime,timedelta,timezone
from fastapi import HTTPException
from app.developer import keys
from app.prospecting import tools
from app.database.prospects import now
from app.platform.context import current
SCOPES={'save_search':'searches:write','enrich_companies':'enrichment:write','create_list':'lists:write','create_task':'tasks:write'}

def public(row):
    result=dict(row);result.pop('fingerprint');result['payload']=json.loads(result.pop('payload_json'));result['result']=json.loads(result.pop('result_json'));return result


def propose(c,kind,arguments,request_id):
    grant=keys.require('mcp:use')
    if kind not in SCOPES:raise HTTPException(422,'This MCP action is unavailable.')
    keys.require(SCOPES[kind])
    if kind=='enrich_companies':keys.require('companies:read')
    if kind=='create_task':
        keys.require('companies:read')
        if arguments.get('contact_id'):keys.require('contacts:read')
    if kind in ('save_search','create_list','create_task'):arguments={**arguments,'request_id':str(uuid.uuid5(uuid.NAMESPACE_URL,'mcp-proposal:'+grant.id+':'+str(request_id)))}
    payload=tools.validate_action(c,kind,arguments);encoded=json.dumps(payload,sort_keys=True);fingerprint=hashlib.sha256(json.dumps([kind,payload],sort_keys=True).encode()).hexdigest();keys.lock(c,grant.organization_id)
    prior=c.execute('SELECT * FROM developer_action_approvals WHERE key_id=? AND request_id=?',(grant.id,str(request_id))).fetchone()
    if prior:
        if prior['fingerprint']!=fingerprint:raise HTTPException(409,'Proposal request ID belongs to different content.')
        return public(prior)
    if c.execute("SELECT COUNT(*) FROM developer_action_approvals WHERE organization_id=? AND status='PENDING' AND expires_at>?",(grant.organization_id,now())).fetchone()[0]>=50:raise HTTPException(429,'Review existing proposals before requesting more actions.')
    identifier=str(uuid.uuid4());c.execute('INSERT INTO developer_action_approvals(id,organization_id,key_id,requested_by,request_id,fingerprint,kind,payload_json,expires_at,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',(identifier,grant.organization_id,grant.id,grant.actor,str(request_id),fingerprint,kind,encoded,(datetime.now(timezone.utc)+timedelta(minutes=30)).isoformat(),now()))
    return public(c.execute('SELECT * FROM developer_action_approvals WHERE id=? AND organization_id=?',(identifier,grant.organization_id)).fetchone())


def status(c,key):
    grant=keys.require('mcp:use');row=c.execute('SELECT * FROM developer_action_approvals WHERE id=? AND organization_id=? AND key_id=?',(key,grant.organization_id,grant.id)).fetchone()
    if not row:raise HTTPException(404,'Proposal not found.')
    return public(row)


def listing(c,page=1):
    context=keys.manager(c)
    return {'items':[public(row) for row in c.execute('SELECT * FROM developer_action_approvals WHERE organization_id=? ORDER BY created_at DESC LIMIT 25 OFFSET ?',(context.organization_id,(page-1)*25)).fetchall()],'page':page,'page_size':25}


def decide(c,key,decision):
    context=keys.manager(c);keys.lock(c,context.organization_id)
    from app.config.settings import get_settings
    if not get_settings().heysow_mcp_enabled:raise HTTPException(503,'MCP actions are disabled.')
    row=c.execute('SELECT * FROM developer_action_approvals WHERE id=? AND organization_id=?',(key,context.organization_id)).fetchone()
    if not row:raise HTTPException(404,'Proposal not found.')
    if row['status']!='PENDING':return public(row)
    if row['expires_at']<now():raise HTTPException(409,'Proposal expired. Request a fresh reviewed proposal.')
    if decision=='decline':
        c.execute("UPDATE developer_action_approvals SET status='DECLINED',decided_at=?,decided_by=? WHERE id=? AND organization_id=?",(now(),context.actor,key,context.organization_id))
    else:
        credential=c.execute('SELECT * FROM workspace_api_keys WHERE id=? AND organization_id=?',(row['key_id'],context.organization_id)).fetchone()
        from app.api.organization import membership_role
        if not credential or credential['revoked_at'] or credential['expires_at']<=now() or membership_role(c,credential['created_by'],context.organization_id) not in ('OWNER','ADMIN','MEMBER'):raise HTTPException(409,'The requesting credential no longer has active write authority.')
        if SCOPES[row['kind']] not in json.loads(credential['scopes_json']):raise HTTPException(409,'The credential no longer grants this action.')
        result=tools.apply(c,key,row['kind'],json.loads(row['payload_json']))
        c.execute("UPDATE developer_action_approvals SET status='APPLIED',result_json=?,decided_at=?,decided_by=? WHERE id=? AND organization_id=?",(json.dumps(result),now(),context.actor,key,context.organization_id))
        c.execute('INSERT INTO audit_log(id,actor,action,entity,result,details_json,organization_id,created_at) VALUES(?,?,?,?,?,?,?,?)',(str(uuid.uuid4()),context.actor,'MCP_PROPOSAL_APPROVED','mcp-proposal:'+key,'SUCCESS',json.dumps({'kind':row['kind'],'key_id':row['key_id']}),context.organization_id,now()))
    return public(c.execute('SELECT * FROM developer_action_approvals WHERE id=? AND organization_id=?',(key,context.organization_id)).fetchone())
