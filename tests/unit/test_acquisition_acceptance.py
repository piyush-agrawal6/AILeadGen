"""Small controlled acquisition state machine; fixture observations, no production flags."""
from datetime import datetime,timezone
from test_automation import db
from app.automation import service
from app.mail.config import MailSettings
from app.database.models import Business
from app.database.repositories import BusinessRepository
from app.database.prospects import ProspectRepository
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID


def test_small_target_rotation_dedup_no_email_history_and_shortfall(db,monkeypatch):
    config=MailSettings(_env_file=None,AUTO_SCAN_ENABLED=True,DAILY_QUALIFIED_LEAD_TARGET=3,MAX_EMAILS_PER_DAY=100,DAILY_EMAIL_TARGET=100)
    monkeypatch.setattr(service,'mail_settings',lambda:config)
    monkeypatch.setattr('app.api.services.cloud_executor.dispatch_queued',lambda:None)
    db.execute('UPDATE automation_controls SET scan_paused=0')
    # Only two configured combinations in the controlled run, preserving quality on exhaustion.
    markets=[r[0] for r in db.execute('SELECT id FROM scan_markets ORDER BY id LIMIT 2').fetchall()]
    db.execute('UPDATE scan_markets SET enabled=0')
    for mid in markets:db.execute('UPDATE scan_markets SET enabled=1 WHERE id=?',(mid,))
    db.commit()
    first=service.legacy_acquisition_tick(db);assert first['status']=='QUEUED'
    assert service.legacy_acquisition_tick(db)['run_id']==first['run_id']
    def observe(rid):
        b=Business(name='Controlled no-email hotel',normalized_name='controlled no-email hotel',vertical='hospitality',city='London',country='United Kingdom',phone='+442055500001',website='https://controlled.invalid',run_id=rid,processing_status='QUALIFIED')
        BusinessRepository(db).insert(b);pid=ProspectRepository(db).observe(b, organization=PLANEBYTE_ORGANIZATION_ID)
        db.execute("UPDATE pipeline_runs SET status='COMPLETED',raw_found=5,qualified=1 WHERE id=?",(rid,));db.commit();return pid
    pid=observe(first['run_id'])
    second=service.legacy_acquisition_tick(db);assert second['status']=='QUEUED' and second['run_id']!=first['run_id']
    assert observe(second['run_id'])==pid
    done=service.legacy_acquisition_tick(db);assert done['status']=='SHORTFALL'
    run=db.execute('SELECT * FROM automation_runs').fetchone()
    assert run['target']==3 and run['new_qualified']==1 and run['shortfall']==2 and run['raw_candidates']==10
    assert db.execute('SELECT COUNT(*) FROM prospect_observations').fetchone()[0]==2
    assert db.execute('SELECT COUNT(*) FROM master_lead_state').fetchone()[0]==1
    assert db.execute('SELECT contact_state FROM master_lead_state').fetchone()[0]=='MANUAL_CONTACT_REQUIRED'
    assert db.execute('SELECT COUNT(*) FROM automation_email_queue').fetchone()[0]==0
    assert db.execute('SELECT COUNT(DISTINCT market_id) FROM automation_scans').fetchone()[0]==2
    assert service.legacy_acquisition_tick(db)['status']=='SHORTFALL'
