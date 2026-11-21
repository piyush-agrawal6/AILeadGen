"""Owned configuration and transactional event outbox. No HTTP on domain writes."""
import hashlib,hmac,json,secrets,uuid
from datetime import datetime,timedelta,timezone
from urllib.parse import urlsplit,urlunsplit
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict,Field,field_validator
from app.api.organization import require_role
from app.config.settings import get_settings
from app.database.prospects import now
from app.integrations.crypto import seal,open_envelope,cipher
from app.platform.context import current,organization

TOPICS=('company.created','contact.created','contact.updated','task.created','task.updated','email.sent','reply.received')
RADAR_TOPICS=('radar.signal.qualified','radar.signal.status_changed','radar.opportunity.created','radar.opportunity.status_changed')
Topic=Literal['company.created','contact.created','contact.updated','task.created','task.updated','email.sent','reply.received','radar.signal.qualified','radar.signal.status_changed','radar.opportunity.created','radar.opportunity.status_changed']

def radar_access(c):
    if not get_settings().radar_webhook_events_enabled:raise HTTPException(503,'Radar event delivery is not enabled.')
    from app.intent_radar.permissions import context
    from app.billing.access_periods import require_paid_feature
    ctx=context(c);require_paid_feature(c,ctx.organization_id,'api_requests')

def radar_allowed(c):
    try:radar_access(c);return True
    except HTTPException:return False

def radar_delivery_ok(c,payload):
    from app.intent_radar import service as radar
    from app.intent_radar.exports import exportable
    radar_access(c);org=organization();data=payload['data']
    if 'opportunity_id' in data:
        row=c.execute('SELECT s.* FROM intent_signals s JOIN intent_opportunities o ON o.organization_id=s.organization_id AND o.signal_id=s.id WHERE o.organization_id=? AND o.id=?',(org,data['opportunity_id'])).fetchone()
    else:row=c.execute('SELECT * FROM intent_signals WHERE organization_id=? AND id=?',(org,data['signal_id'])).fetchone()
    return bool(row and exportable(radar.decode(row),radar.preferences(c)['source_retention_days']))

class Endpoint(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    name:str=Field(min_length=2,max_length=100)
    url:str=Field(min_length=10,max_length=1000)
    topics:list[Topic]=Field(min_length=1,max_length=11)
    revision:int|None=Field(None,ge=1)
    request_id:uuid.UUID=Field(default_factory=uuid.uuid4)
    @field_validator('url')
    @classmethod
    def public_https(cls,value):
        from app.utils.urls import is_safe_url
        p=urlsplit(value)
        if p.scheme!='https' or p.username or p.password or p.query or p.fragment or p.port not in (None,443) or not is_safe_url(value,check_dns=False):
            raise ValueError('Use a public HTTPS endpoint without credentials, query parameters or redirects.')
        return urlunsplit(('https',p.netloc.lower(),p.path or '/','',''))

def enabled():
    if not get_settings().heysow_webhooks_enabled:raise HTTPException(503,'Webhooks are disabled.')

def manager(c):
    enabled();org=organization();require_role(c,current().actor,org,('OWNER','ADMIN'));return org

def owned(c,key):
    org=manager(c);row=c.execute('SELECT * FROM webhook_endpoints WHERE id=? AND organization_id=?',(key,org)).fetchone()
    if not row:raise HTTPException(404,'Webhook endpoint not found.')
    return dict(row)

def view(row):
    return {key:row[key] for key in ('id','name','url','status','revision','created_at','updated_at','last_error_code')}|{'topics':json.loads(row['topics_json'])}

def envelope(row):return {'organization_id':row['organization_id'],'connection_id':row['id'],'provider':'WEBHOOK','purpose':'SIGNING_SECRET'}

def audit(c,key,action):
    c.execute('INSERT INTO audit_log(id,actor,action,entity,result,organization_id,created_at) VALUES(?,?,?,?,?,?,?)',
              (str(uuid.uuid4()),current().actor,action,'webhook:'+key,'SUCCESS',organization(),now()))

def listing(c):
    org=manager(c)
    from app.api.organization import products
    try:cipher();configured=True
    except HTTPException:configured=False
    return {'items':[view(dict(row)) for row in c.execute('SELECT * FROM webhook_endpoints WHERE organization_id=? ORDER BY created_at DESC LIMIT 20',(org,)).fetchall()],
            'configured':configured,'available_topics':(TOPICS if products(c,org).get('LEADGEN') else ())+ (RADAR_TOPICS if radar_allowed(c) else ()),'delivery_semantics':'AT_LEAST_ONCE','max_attempts':5,'max_endpoints':10}

def save(c,body,key=None):
    org=manager(c);cipher()
    if any(t in RADAR_TOPICS for t in body.topics):radar_access(c)
    from app.api.organization import products
    if any(t in TOPICS for t in body.topics) and not products(c,org).get('LEADGEN'):raise HTTPException(403,'Lead Engine event topics are unavailable.')
    from app.workflows.service import lock
    lock(c);manager(c);stamp=now()
    if key:
        previous=owned(c,key)
        if previous['status']=='ARCHIVED':raise HTTPException(409,'Archived endpoints retain history and cannot be edited.')
        if body.revision!=previous['revision']:raise HTTPException(409,'Endpoint changed. Reload before saving.')
        c.execute('UPDATE webhook_endpoints SET name=?,url=?,topics_json=?,revision=revision+1,updated_at=? WHERE id=? AND organization_id=? AND revision=?',
                  (body.name,body.url,json.dumps(list(dict.fromkeys(body.topics))),stamp,key,org,body.revision));secret=None
    else:
        fingerprint=hashlib.sha256(json.dumps([body.name,body.url,sorted(set(body.topics))]).encode()).hexdigest()
        previous=c.execute('SELECT * FROM webhook_endpoints WHERE organization_id=? AND request_id=?',(org,str(body.request_id))).fetchone()
        if previous:
            if previous['creation_fingerprint']!=fingerprint or previous['created_by']!=current().actor:raise HTTPException(409,'Webhook request ID belongs to different content.')
            return {'endpoint':view(dict(previous)),'already_created':True}
        if c.execute("SELECT COUNT(*) FROM webhook_endpoints WHERE organization_id=? AND status<>'ARCHIVED'",(org,)).fetchone()[0]>=10:raise HTTPException(429,'Archive an endpoint before adding another.')
        key=str(uuid.uuid4());secret=secrets.token_urlsafe(32);row={'organization_id':org,'id':key}
        encrypted=seal({'secret':secret},**envelope(row))
        c.execute('INSERT INTO webhook_endpoints(id,organization_id,name,url,topics_json,signing_secret_ciphertext,created_by,created_at,updated_at,request_id,creation_fingerprint) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                  (key,org,body.name,body.url,json.dumps(list(dict.fromkeys(body.topics))),encrypted,current().actor,stamp,stamp,str(body.request_id),fingerprint))
    audit(c,key,'WEBHOOK_SAVED');return {'endpoint':view(owned(c,key)),**({'signing_secret':secret} if secret else {})}

def control(c,key,action,revision):
    row=owned(c,key);org=manager(c)
    if row['status']=='ARCHIVED':raise HTTPException(409,'This endpoint is archived.')
    from app.workflows.service import lock
    lock(c)
    if row['revision']!=revision:raise HTTPException(409,'Endpoint changed. Reload before changing it.')
    secret=None
    if action=='rotate':
        secret=secrets.token_urlsafe(32);encrypted=seal({'secret':secret},**envelope(row))
        changed=c.execute('UPDATE webhook_endpoints SET signing_secret_ciphertext=?,revision=revision+1,updated_at=? WHERE id=? AND organization_id=? AND revision=?',(encrypted,now(),key,org,revision)).rowcount
    else:
        state={'pause':'PAUSED','resume':'ACTIVE','archive':'ARCHIVED'}[action]
        changed=c.execute('UPDATE webhook_endpoints SET status=?,revision=revision+1,updated_at=?,last_error_code=NULL WHERE id=? AND organization_id=? AND revision=?',(state,now(),key,org,revision)).rowcount
    if not changed:raise HTTPException(409,'Endpoint changed. Reload before changing it.')
    audit(c,key,'WEBHOOK_'+action.upper());return {'endpoint':view(owned(c,key)),**({'signing_secret':secret} if secret else {})}

def emit(c,topic,event_key,data):
    if not get_settings().heysow_webhooks_enabled:return
    if topic in RADAR_TOPICS and not get_settings().radar_webhook_events_enabled:return
    org=organization();stamp=now()
    if topic not in TOPICS+RADAR_TOPICS:raise ValueError('Unsupported webhook topic')
    # Only identifiers: subscribers use their separately scoped API key for detail.
    radar=topic in RADAR_TOPICS
    if radar:
        field='signal_id' if topic.startswith('radar.signal.') else 'opportunity_id'
        if set(data)!={field} or str(uuid.UUID(data[field]))!=data[field]:raise ValueError('Invalid Radar event reference')
    elif set(data)-{'business_id','prospect_id','contact_id','task_id','message_id'}:raise ValueError('Unsupported event data')
    if any(not isinstance(value,(str,int)) or isinstance(value,bool) or len(str(value))>100 for value in data.values()):raise ValueError('Event identifiers must be bounded scalar values')
    payload={'id':str(uuid.uuid5(uuid.NAMESPACE_URL,org+':'+topic+':'+event_key)),'type':topic,'created_at':stamp,'workspace_id':org,'data':data}
    if radar:
        if not c.execute("SELECT 1 FROM webhook_endpoints WHERE organization_id=? AND status='ACTIVE' AND topics_json LIKE ? LIMIT 1",(org,'%"'+topic+'"%')).fetchone():return
        try:
            if not radar_delivery_ok(c,payload):return
        except HTTPException:return
        payload.update(schema_version=1,resource='/api/v1/intent-radar/'+('signals' if field=='signal_id' else 'opportunities')+'/'+data[field])
    encoded=json.dumps(payload,separators=(',',':'),sort_keys=True)
    if len(encoded)>8000:raise ValueError('Webhook event exceeds its budget')
    pending=c.execute("SELECT COUNT(*) FROM webhook_deliveries WHERE organization_id=? AND status IN ('QUEUED','RETRY','DELIVERING')",(org,)).fetchone()[0]
    for endpoint in c.execute("SELECT id,topics_json FROM webhook_endpoints WHERE organization_id=? AND status='ACTIVE' LIMIT 10",(org,)).fetchall():
        if topic not in json.loads(endpoint['topics_json']):continue
        if pending>=5000:
            c.execute("UPDATE webhook_endpoints SET status='PAUSED',last_error_code='OUTBOX_CAPACITY',updated_at=? WHERE id=? AND organization_id=?",(stamp,endpoint['id'],org));continue
        changed=c.execute('INSERT INTO webhook_deliveries(id,endpoint_id,organization_id,event_id,topic,body_json,next_attempt_at,created_at) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(endpoint_id,event_id) DO NOTHING',
                          (str(uuid.uuid4()),endpoint['id'],org,payload['id'],topic,encoded,stamp,stamp)).rowcount
        pending+=changed

def history(c,key,page=1,size=25):
    row=owned(c,key);org=row['organization_id']
    total=c.execute('SELECT COUNT(*) FROM webhook_deliveries WHERE endpoint_id=? AND organization_id=?',(key,org)).fetchone()[0]
    rows=c.execute('SELECT id,event_id,topic,status,attempts,next_attempt_at,last_http_status,last_error_code,created_at,delivered_at FROM webhook_deliveries WHERE endpoint_id=? AND organization_id=? ORDER BY created_at DESC,id LIMIT ? OFFSET ?',(key,org,size,(page-1)*size)).fetchall()
    return {'endpoint':view(row),'items':[dict(item) for item in rows],'total':total,'page':page,'page_size':size}

def retry(c,key,delivery_id):
    row=owned(c,key)
    if row['status']!='ACTIVE':raise HTTPException(409,'Resume the endpoint before retrying delivery.')
    changed=c.execute("UPDATE webhook_deliveries SET status='RETRY',next_attempt_at=?,lease_owner=NULL,lease_until=NULL WHERE id=? AND endpoint_id=? AND organization_id=? AND attempts<5 AND status IN ('FAILED','RETRY')",(now(),delivery_id,key,row['organization_id'])).rowcount
    if not changed:raise HTTPException(409,'Delivery is unavailable, complete or has exhausted its attempts.')
    audit(c,key,'WEBHOOK_DELIVERY_RETRY');return {'queued':True}

def signature(secret,timestamp,body):
    return 'v1='+hmac.new(secret.encode(),str(timestamp).encode()+b'.'+body,hashlib.sha256).hexdigest()
