import re
import time
import urllib.parse
import uuid
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from app.api.dependencies import get_db
from app.config.settings import get_settings
from app.platform.product_help import search

router=APIRouter(prefix='/help',tags=['Product help'])
SUPPORT_EMAIL='contact@planebyte.com'


class SupportDiagnostics(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    request_id:str|None=Field(default=None,max_length=80)
    app_version:str|None=Field(default=None,max_length=40)
    timestamp:str|None=Field(default=None,max_length=64)
    viewport:str|None=Field(default=None,max_length=40)


class SupportRequest(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    category:Literal['support','bug','billing','feature']='support'
    subject:str=Field(min_length=4,max_length=160)
    description:str=Field(min_length=10,max_length=3000)
    affected_page:str|None=Field(default=None,max_length=200)
    include_diagnostics:bool=False
    diagnostics:SupportDiagnostics|None=None


_SECRET_PATTERNS=re.compile(r'(?i)(bearer\s+[a-z0-9._-]{12,}|pb_live_[a-z0-9_-]{8,}|re_[a-z0-9_-]{12,}|sk_[a-z0-9_-]{12,}|ghp_[a-z0-9]{12,}|api[_-]?key\s*[:=]\s*\S+)')


def _scrub(text:str)->str:
    return _SECRET_PATTERNS.sub('[redacted]',text)


@router.get('/topics')
def topics(query:str=Query('',max_length=200)):
    from app.platform.context import current
    current()
    return {'items':search(query,12),'support_email':SUPPORT_EMAIL}


@router.post('/support')
def submit_support(body:SupportRequest,request:Request,c=Depends(get_db,scope='function')):
    from app.accounts import security
    from app.notifications import transactional as mail

    actor=getattr(request.state,'user_email',None)
    org=getattr(request.state,'organization_id',None)
    if not actor:
        raise HTTPException(401,'Authentication required.')
    if security.limited(c,'help-support-request',actor,5,3600):
        raise HTTPException(429,'Support request limit reached (5 per hour). You can also email contact@planebyte.com directly.')

    clean_subject=_scrub(body.subject)
    clean_desc=_scrub(body.description)
    clean_page=_scrub(body.affected_page or '')[:200]
    lines=[
        f'Category: {body.category.upper()}',
        f'From: {actor}',
        f'Workspace ID: {org or "none"}',
    ]
    if clean_page:
        lines.append(f'Affected page: {clean_page}')
    lines.extend(['', clean_desc])
    if body.include_diagnostics and body.diagnostics:
        lines.extend([
            '',
            '--- Consented Diagnostic Metadata ---',
            f'Request ID: {body.diagnostics.request_id or "n/a"}',
            f'App Version: {body.diagnostics.app_version or "n/a"}',
            f'Timestamp: {body.diagnostics.timestamp or "n/a"}',
            f'Viewport: {body.diagnostics.viewport or "n/a"}',
        ])
    summary='\n'.join(lines)
    fallback_mailto=(
        f'mailto:{SUPPORT_EMAIL}'
        f'?subject={urllib.parse.quote(f"[PlaneByte {body.category.upper()}] {clean_subject}")}'
        f'&body={urllib.parse.quote(summary[:1800])}'
    )

    if not get_settings().transactional_mail_enabled or not mail.configured():
        return {
            'delivered':False,
            'support_email':SUPPORT_EMAIL,
            'fallback_mailto':fallback_mailto,
            'message':'Automated support email delivery is currently unavailable in this environment. Use the prefilled email link below to contact PlaneByte Support directly.',
        }

    ref_id=str(uuid.uuid4())
    nid=mail.queue(
        c,
        SUPPORT_EMAIL,
        'SUPPORT_REQUEST',
        ref_id,
        {'category':body.category,'subject':clean_subject,'summary':summary},
        dedupe_key=f'support:{actor}:{int(time.time())}:{ref_id[:8]}',
        expires_at=int(time.time())+3600,
        organization_id=org,
        reply_to=actor,
    )
    c.commit()
    try:
        mail.deliver(nid)
    except Exception:
        return {
            'delivered':False,
            'support_email':SUPPORT_EMAIL,
            'fallback_mailto':fallback_mailto,
            'message':'We could not confirm delivery through the mail provider right now. Use the prefilled email link below so your message is not lost.',
        }
    row=c.execute('SELECT status,provider_message_id,error_code FROM transactional_notifications WHERE id=?',(nid,)).fetchone()
    status=row['status'] if row else 'UNKNOWN'
    if status in ('ACCEPTED','DELIVERED'):
        return {
            'delivered':True,
            'reference_id':ref_id[:8].upper(),
            'provider_message_id':row['provider_message_id'],
            'support_email':SUPPORT_EMAIL,
            'message':f'Support request delivered to {SUPPORT_EMAIL} (Ref: {ref_id[:8].upper()}). Replies will go to {actor}.',
        }
    return {
        'delivered':False,
        'support_email':SUPPORT_EMAIL,
        'fallback_mailto':fallback_mailto,
        'message':f'Automated email delivery could not be confirmed ({row["error_code"] if row else status}). Use the prefilled email link below to reach {SUPPORT_EMAIL}.',
    }
