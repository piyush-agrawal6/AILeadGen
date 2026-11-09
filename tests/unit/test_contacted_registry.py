"""Permanent memory survives operational deletion; actual message identity is the unit."""
import sqlite3
from collections import Counter
import pytest
from fastapi import HTTPException
from app.database.contactable_schema import CONTACTABLE_SQL
from app.mail import contacted
from app.outreach import fixed

@pytest.fixture
def registry():
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
    c.executescript("CREATE TABLE schema_migrations(version INTEGER);INSERT INTO schema_migrations VALUES(15);CREATE TABLE email_messages(id TEXT,prospect_id TEXT,to_address TEXT,status TEXT,direction TEXT,idempotency_key TEXT);")
    c.executescript(CONTACTABLE_SQL)
    c.executescript("CREATE TABLE organizations(id TEXT PRIMARY KEY,status TEXT);CREATE TABLE organization_memberships(organization_id TEXT,user_id TEXT,role TEXT,status TEXT);INSERT INTO organizations VALUES('planebyte','ACTIVE');INSERT INTO organization_memberships VALUES('planebyte','registry-owner','OWNER','ACTIVE');")
    from app.platform.context import workspace_scope
    with workspace_scope(c,'registry-owner','planebyte'):
        yield c
    c.close()

def add(c,mid='m1',email=' Sales@Example.com ',org='planebyte',at='2026-11-03T01:00:00+00:00'):
    return contacted.record(c,message_id=mid,email=email,sent_at=at,provider_message_id='<'+mid+'@smtp>',organization_id=org)

def test_only_actual_record_creates_memory_and_retries_do_not_increment(registry):
    c=registry;c.execute("INSERT INTO email_messages(id,to_address,status,direction,idempotency_key) VALUES('draft','draft@example.com','QUEUED','OUTBOUND','k')")
    contacted.record_message(c,'draft');assert not contacted.lookup(c,'draft@example.com')
    assert add(c);assert not add(c);assert contacted.lookup(c,'sales@example.com')['send_count']==1
    assert add(c,'m2');assert contacted.lookup(c,'sales@example.com')['send_count']==2

def test_exact_address_tenant_safe_no_domain_or_mailbox_rewriting(registry):
    c=registry;add(c)
    with pytest.raises(HTTPException):contacted.ensure_new(c,' SALES@EXAMPLE.COM ')
    contacted.ensure_new(c,'marketing@example.com');contacted.ensure_new(c,'sales+new@example.com')
    with pytest.raises(HTTPException):contacted.ensure_new(c,'sales@example.com',organization_id='another-company')
    with pytest.raises(HTTPException):add(c,'other','sales@example.com','another-company')
    assert c.execute('SELECT COUNT(*) FROM contacted_recipients').fetchone()[0]==1  # Cross-tenant overrides cannot write; independent scopes are covered in stabilization tests.

def test_unrelated_pending_reservation_blocks_same_email(registry):
    c=registry;c.execute("INSERT INTO email_messages(id,to_address,status,direction,idempotency_key) VALUES('pending','sales@example.com','SENDING','OUTBOUND','first')")
    with pytest.raises(HTTPException):contacted.ensure_new(c,'sales@example.com',idempotency_key='second')
    contacted.ensure_new(c,'sales@example.com',idempotency_key='first')

def test_memory_survives_operational_rows_cleared_and_earliest_latest_are_correct(registry):
    c=registry;add(c,at='2026-11-03T02:00:00+00:00');add(c,'earlier',at='2026-11-02T01:00:00+00:00');c.execute('DELETE FROM email_messages')
    r=contacted.lookup(c,'sales@example.com');assert r['first_message_id']=='earlier';assert r['last_message_id']=='m1';assert r['send_count']==2
    with pytest.raises(HTTPException):contacted.ensure_new(c,'sales@example.com')

def test_message_identity_cannot_be_reused_for_another_recipient(registry):
    add(registry)
    with pytest.raises(ValueError):add(registry,email='another@example.com')

def test_five_exact_fixed_templates_balanced_without_ai():
    counts=Counter();assignment=[]
    for i in range(100):
        tid=fixed.assign('controlled-lead-'+str(i),counts);counts[tid]+=1;assignment.append(tid)
        email=fixed.render('Example Dental',tid)
        assert email['body_text']==fixed.TEMPLATES[tid]['body_text'].replace('{{company_name}}','Example Dental')
        assert email['subject']==fixed.TEMPLATES[tid]['subject'].replace('{{company_name}}','Example Dental')
        assert '{{' not in email['body_text'];assert 80<=len(email['body_text'].split())<=130
        assert email['pdf_asset_id']==fixed.ASSET_ID and email['pdf_version']=='v1'
    assert set(counts.values())=={20}
    again=Counter();assert assignment==[choose(again,i) for i in range(100)]

def choose(counts,i):
    tid=fixed.assign('controlled-lead-'+str(i),counts);counts[tid]+=1;return tid

def test_archived_reply_requires_authenticated_exact_peer_and_reference(registry,monkeypatch):
    from datetime import datetime,timezone
    from email.utils import format_datetime
    from types import SimpleNamespace
    c=registry
    c.execute('CREATE TABLE email_address_suppressions(address TEXT PRIMARY KEY,source TEXT,status TEXT,updated_at TEXT,organization_id TEXT)')
    at=datetime.now(timezone.utc);contacted.record(c,message_id='old',provider_message_id='<old@smtp>',email='sales@example.com',sent_at=at.isoformat())
    monkeypatch.setattr('app.mail.config.mail_settings',lambda:SimpleNamespace(from_address='planebyte@gmail.com'))
    message={'references':['<old@smtp>'],'from':'sales@example.com','to':'planebyte@gmail.com','date':format_datetime(at),'body_text':'Yes please, send the scope','authentication':'mx.google.com; dmarc=pass header.from=example.com'}
    assert not contacted.archived_reply(c,message|{'from':'someone@example.com'})
    assert not contacted.archived_reply(c,message|{'references':['<unknown@smtp>']})
    assert not contacted.archived_reply(c,message|{'authentication':''})
    assert contacted.archived_reply(c,message)
    assert contacted.lookup(c,'sales@example.com')['ever_positive_reply']==1
    assert contacted.archived_reply(c,message|{'body_text':'Please remove me'})
    assert contacted.lookup(c,'sales@example.com')['do_not_contact']==1
    assert c.execute('SELECT COUNT(*) FROM email_address_suppressions').fetchone()[0]==1
    assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0
