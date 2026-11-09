import hashlib,json,uuid
from pathlib import Path
import pytest
from fastapi import HTTPException
from test_phase4 import workspace
from campaign_fixtures import campaign
from app.outreach import fixed
from app.outreach.capabilities_pdf import generate
from app.mail import service,tracking,contacted
from app.database.prospects import now

def test_archived_universal_attachment_cannot_start_new_outreach(workspace,tmp_path,monkeypatch):
    monkeypatch.setattr('app.platform.modules.legacy_enabled',lambda:True)
    c,b,pid,config,transport=workspace;config.mode='production';config.live_approved=True;config.from_address='planebyte@gmail.com';config.from_name='PlaneByte'
    transport.health_check.return_value={'smtp':'READY','imap':'READY'}
    cid=campaign(c);c.execute('UPDATE pipeline_runs SET campaign_id=? WHERE id=?',(cid,b.run_id));fixed.seed(c)
    pdf=generate(tmp_path/'capabilities.pdf');raw=pdf.read_bytes()
    from app.storage import LocalArtifactStorage
    storage=LocalArtifactStorage(tmp_path/'assets');key='audits/company-assets/planebyte-capabilities-v1.pdf';storage.put(key,pdf,'application/pdf');monkeypatch.setattr('app.storage.artifact_storage',lambda:storage)
    c.execute('INSERT INTO company_pdf_assets VALUES(?,?,?,?,?,?,?,?,?,?)',(fixed.ASSET_ID,'v1',contacted.organization(),'PlaneByte Capabilities & Services.pdf',key,hashlib.sha256(raw).hexdigest(),len(raw),3,1,now()))
    body=fixed.render(b.name,'PB_INTRO_01')|{'campaign_id':cid,'to_address':b.public_email,'preview_nonce':str(uuid.uuid4()),'idempotency_key':str(uuid.uuid4()),'confirmation':'SEND','track_opens':True,'track_clicks':True}
    with pytest.raises(HTTPException) as denied:service.preview(c,pid,'founder@example.com',body)
    assert denied.value.status_code==409
    assert contacted.lookup(c,b.public_email) is None
    assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0
    assert c.execute('SELECT COUNT(*) FROM company_pdf_assets').fetchone()[0]==1
    transport.send_message.assert_not_called()
