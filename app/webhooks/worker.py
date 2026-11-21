"""Bounded public-HTTPS delivery. A stable event/delivery ID enables receiver dedupe."""
import asyncio,json,random,secrets,time,uuid
from datetime import datetime,timedelta,timezone
import httpx
from fastapi import HTTPException
from app.database.connection import db_session
from app.database.prospects import now
from app.platform.context import job_scope
from app.webhooks import service
from app.utils.public_transport import PublicAsyncTransport


async def deliver(c,endpoint_id,delivery_id,transport=None):
    row=service.owned(c,endpoint_id)
    from app.config.settings import get_settings
    if get_settings().app_env=='test' and transport is None:raise HTTPException(503,'External webhook requests are disabled in offline tests.')
    if row['status']!='ACTIVE':return 'PAUSED'
    # Revalidate the stored URL before every attempt, then pin public DNS in the transport.
    service.Endpoint(name=row['name'],url=row['url'],topics=json.loads(row['topics_json']))
    lease=secrets.token_hex(16);stamp=now();expiry=(datetime.now(timezone.utc)+timedelta(seconds=45)).isoformat()
    changed=c.execute("""UPDATE webhook_deliveries SET status='DELIVERING',lease_owner=?,lease_until=?,attempts=attempts+1
        WHERE id=? AND endpoint_id=? AND organization_id=? AND attempts<5 AND
        ((status IN ('QUEUED','RETRY') AND next_attempt_at<=?) OR (status='DELIVERING' AND lease_until<?))""",
        (lease,expiry,delivery_id,endpoint_id,row['organization_id'],stamp,stamp)).rowcount
    if not changed:return 'NOT_DUE'
    delivery=dict(c.execute('SELECT * FROM webhook_deliveries WHERE id=? AND organization_id=?',(delivery_id,row['organization_id'])).fetchone());attempt=delivery['attempts']
    c.execute('INSERT INTO webhook_delivery_attempts(delivery_id,organization_id,attempt,started_at) VALUES(?,?,?,?)',(delivery_id,row['organization_id'],attempt,stamp));c.commit()
    error=None;status=None;retry_after=0
    try:
        latest=service.owned(c,endpoint_id)
        if latest['status']!='ACTIVE' or latest['revision']!=row['revision']:raise HTTPException(409,'Endpoint changed before delivery.')
        if delivery['topic'] not in json.loads(latest['topics_json']):raise HTTPException(409,'Topic no longer subscribed.')
        if delivery['topic'] in service.RADAR_TOPICS and not service.radar_delivery_ok(c,json.loads(delivery['body_json'])):raise HTTPException(409,'Event is no longer eligible for delivery.')
        secret=service.open_envelope(row['signing_secret_ciphertext'],**service.envelope(row))['secret']
        body=delivery['body_json'].encode();timestamp=str(int(time.time()))
        headers={'Content-Type':'application/json','User-Agent':'PlaneByte-Webhooks/1.0',
            'X-PlaneByte-Event-ID':delivery['event_id'],'X-PlaneByte-Delivery-ID':delivery_id,
            'X-PlaneByte-Timestamp':timestamp,'X-PlaneByte-Signature':service.signature(secret,timestamp,body),
            'Idempotency-Key':delivery_id}
        async with asyncio.timeout(12):
            async with httpx.AsyncClient(transport=transport or PublicAsyncTransport(),timeout=httpx.Timeout(10,connect=4),follow_redirects=False,trust_env=False) as client:
                async with client.stream('POST',row['url'],content=body,headers=headers) as response:
                    # No response body is read, persisted or logged.
                    status=response.status_code
                    raw=response.headers.get('Retry-After','')[:128]
                    if raw.isdigit():retry_after=min(86400,int(raw))
                    elif raw:
                        from email.utils import parsedate_to_datetime
                        try:retry_after=max(0,min(86400,int((parsedate_to_datetime(raw)-datetime.now(timezone.utc)).total_seconds())))
                        except (ValueError,TypeError,OverflowError):pass
        if not 200<=status<300:error='HTTP_'+str(status)
    except HTTPException:error='ENDPOINT_UNAVAILABLE'
    except (httpx.HTTPError,TimeoutError,asyncio.TimeoutError):error='PUBLIC_HTTPS_REQUEST_FAILED'
    except Exception:error='DELIVERY_CONFIGURATION_FAILED'
    permanent=status in (301,302,303,307,308,400,401,403,404,410,413,422) or error in ('ENDPOINT_UNAVAILABLE','DELIVERY_CONFIGURATION_FAILED')
    state='DELIVERED' if error is None else 'FAILED' if permanent or attempt>=5 else 'RETRY'
    delay=max(retry_after,(60,300,900,3600,7200)[min(attempt-1,4)])+random.uniform(0,5)
    due=(datetime.now(timezone.utc)+timedelta(seconds=delay)).isoformat()
    finished=now()
    c.execute('UPDATE webhook_delivery_attempts SET finished_at=?,http_status=?,error_code=? WHERE delivery_id=? AND organization_id=? AND attempt=?',(finished,status,error,delivery_id,row['organization_id'],attempt))
    c.execute('''UPDATE webhook_deliveries SET status=?,next_attempt_at=?,last_http_status=?,last_error_code=?,delivered_at=?,lease_owner=NULL,lease_until=NULL
        WHERE id=? AND organization_id=? AND lease_owner=?''',(state,due,status,error,finished if state=='DELIVERED' else None,delivery_id,row['organization_id'],lease))
    if permanent and status in (301,302,303,307,308,401,403,404,410):
        c.execute("UPDATE webhook_endpoints SET status='PAUSED',last_error_code=?,updated_at=? WHERE id=? AND organization_id=? AND revision=?",(error,finished,endpoint_id,row['organization_id'],row['revision']))
    c.commit();return state


async def execute_async(key,db_path=None,transport=None,dispatch_token=None):
    service.enabled();deadline=time.monotonic()+120
    with db_session(db_path) as c:
        with job_scope(c,'webhook',key):
            endpoint=None
            try:
                endpoint=service.owned(c,key)
                if endpoint['status']!='ACTIVE':return
                # A crash during the final reserved attempt has an uncertain outcome;
                # retain that fact without sending a sixth request or leaving it stuck.
                c.execute("UPDATE webhook_deliveries SET status='FAILED',last_error_code='DELIVERY_OUTCOME_UNKNOWN',lease_owner=NULL,lease_until=NULL WHERE endpoint_id=? AND organization_id=? AND status='DELIVERING' AND attempts>=5 AND lease_until<?",(key,endpoint['organization_id'],now()))
                c.commit()
                ids=[row[0] for row in c.execute("SELECT id FROM webhook_deliveries WHERE endpoint_id=? AND organization_id=? AND attempts<5 AND ((status IN ('QUEUED','RETRY') AND next_attempt_at<=?) OR (status='DELIVERING' AND lease_until<?)) ORDER BY created_at LIMIT 20",(key,endpoint['organization_id'],now(),now())).fetchall()]
                for delivery_id in ids:
                    if time.monotonic()>deadline:break
                    await deliver(c,key,delivery_id,transport)
            finally:
                if dispatch_token and endpoint:c.execute('UPDATE webhook_endpoints SET dispatch_token=NULL,dispatch_until=NULL WHERE id=? AND organization_id=? AND dispatch_token=?',(key,endpoint['organization_id'],dispatch_token))


def execute(key,db_path=None,dispatch_token=None):
    service.enabled()
    return asyncio.run(execute_async(key,db_path,dispatch_token=dispatch_token))
