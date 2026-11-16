"""Mailbox control is verified separately; a work-looking domain proves no ownership."""
import json,re
from pathlib import Path
from fastapi import HTTPException
from app.utils.urls import _tld_extractor

POLICY=json.loads(Path(__file__).with_name('email_policy.json').read_text())
BLOCKED=frozenset((*POLICY['personal_domains'],*POLICY['disposable_domains']))
MESSAGE='Please use your company email address to create a PlaneByte workspace.'

def normalize(value):
    value=value.strip().lower() if isinstance(value,str) else ''
    if len(value)>254 or not re.fullmatch(r'[a-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-z0-9.-]+\.[a-z]{2,63}',value) or len(value.split('@')[0])>64:
        raise ValueError('Enter a valid work email address.')
    local,domain=value.rsplit('@',1)
    if local.startswith('.') or local.endswith('.') or '..' in local or any(not label or len(label)>63 or label.startswith('-') or label.endswith('-') for label in domain.split('.')):
        raise ValueError('Enter a valid work email address.')
    return value

def work_email(value):
    value=normalize(value);domain=value.rsplit('@',1)[1]
    parsed=_tld_extractor(domain)
    if not parsed.domain or not parsed.suffix or domain in BLOCKED or any(domain.endswith('.'+blocked) for blocked in BLOCKED):raise ValueError(MESSAGE)
    return value

def company_domain(email):
    return _tld_extractor(work_email(email).rsplit('@',1)[1]).top_domain_under_public_suffix

def mailbox_domain_available(email):
    # DNS is an availability check, never proof that this user owns a company.
    import dns.resolver
    try:return any(str(record.exchange)!='.' for record in dns.resolver.resolve(email.rsplit('@',1)[1],'MX',lifetime=4))
    except dns.resolver.NXDOMAIN:return False
    except dns.resolver.NoAnswer:return False
    except Exception:raise HTTPException(503,'The company email domain could not be checked. Retry shortly.') from None
