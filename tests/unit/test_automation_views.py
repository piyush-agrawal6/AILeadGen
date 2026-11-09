from test_automation import db
from app.automation.views import search
from app.automation.settings import effective_settings,save_targets
from app.database.models import Business,PipelineRun
from app.database.repositories import BusinessRepository,PipelineRunRepository
from app.database.prospects import ProspectRepository,now
from app.automation.service import reconcile
import json
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID


def test_tab_counts_filters_and_stable_pagination(db):
    run=PipelineRun(market='Controlled',vertical='dentists',target=3);rid=PipelineRunRepository(db).create(run, organization=PLANEBYTE_ORGANIZATION_ID)
    ids=[]
    for i in range(3):
        b=Business(name=f'Fixture {i}',normalized_name=f'fixture {i}',vertical='dentists',city='London',country='United Kingdom',run_id=rid,phone=f'+44205555555{i}',website=f'https://fixture-{i}.invalid',processing_status='QUALIFIED')
        BusinessRepository(db).insert(b);ids.append(ProspectRepository(db).observe(b, organization=PLANEBYTE_ORGANIZATION_ID))
    reconcile(db)
    first=search(db,{},'all',1,2);second=search(db,{},'all',2,2)
    assert first['total']==3 and len(first['items'])==2 and len(second['items'])==1
    assert not {r['prospect_id'] for r in first['items']}.intersection(r['prospect_id'] for r in second['items'])
    assert first['counts']['manual']==3 and first['counts']['today']==3
    assert search(db,{'email_availability':'yes'})['total']==0
    assert search(db,{'country':'United Kingdom','city':'London','vertical':'dentists','email_availability':'no'})['total']==3
    assert search(db,{'search':'Fixture 2'})['total']==1
    db.execute("UPDATE master_lead_state SET sales_state='WON' WHERE prospect_id=?",(ids[0],))
    assert search(db,{},'won')['total']==1


def test_targets_preserve_preferences_and_cannot_enable_environment_flags(db,monkeypatch):
    from app.mail.config import MailSettings
    monkeypatch.setattr('app.automation.settings.mail_settings',lambda:MailSettings(_env_file=None,MAX_EMAILS_PER_DAY=100,DAILY_EMAIL_TARGET=100,AUTO_EMAIL_ENABLED=False,EMAIL_SENDING_ENABLED=False))
    db.execute('INSERT INTO shared_settings(id,configuration_json,updated_by,updated_at,organization_id) VALUES(1,?,?,?,?)',(json.dumps({'general':{'default_target':37}}),'system',now(),PLANEBYTE_ORGANIZATION_ID))
    save_targets(db,{'daily_qualified_lead_target':3,'daily_email_target':2,'max_hour':2,'max_day':5},'system')
    assert json.loads(db.execute('SELECT configuration_json FROM shared_settings').fetchone()[0])['general']['default_target']==37
    s=effective_settings(db)
    assert s.daily_qualified_lead_target==3 and s.max_hour==2 and s.max_day==5
    assert not s.automatic_sending_enabled
