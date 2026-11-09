"""Full controlled lifecycle through existing tracking HTTP handlers; no real send."""
import re
from fastapi.testclient import TestClient
from test_phase41 import sent
from test_phase4 import workspace
from app.api.server import app
from app.api.dependencies import get_db
from app.mail import tracking,service
from app.automation.service import reconcile


def test_tracking_signals_timeline_and_real_unsubscribe_state(sent):
    c,pid,config,transport,result=sent
    c.execute("UPDATE businesses SET processing_status='QUALIFIED' WHERE prospect_id=?",(pid,))
    reconcile(c)
    message=transport.send_message.call_args[0][0]
    rich=message.get_body(preferencelist=('html',)).get_content()
    tokens={kind:token for kind,token in re.findall(r'https://leads.planebyte.com/t/([ocu])/([A-Za-z0-9_-]{43})',rich)}
    app.dependency_overrides[get_db]=lambda:c
    try:
        with TestClient(app) as client:
            headers={'user-agent':'Mozilla/5.0 ControlledAcceptance','sec-fetch-user':'?1'}
            assert client.get('/api/tracking/o/'+tokens['o']+'.gif',headers=headers).status_code==200
            assert client.get('/api/tracking/c/'+tokens['c'],headers=headers,follow_redirects=False).status_code==302
            assert client.get('/api/tracking/u/'+tokens['u']).status_code==200
            assert c.execute('SELECT suppressed_at FROM prospect_sales WHERE prospect_id=?',(pid,)).fetchone()[0] is None
            # Production semantics exercised on isolated fixture data only.
            c.execute('UPDATE email_messages SET test_mode=0 WHERE id=?',(result['id'],))
            assert client.post('/api/tracking/u/'+tokens['u'],content='confirm=stop').status_code==200
            assert c.execute('SELECT contact_state FROM master_lead_state WHERE prospect_id=?',(pid,)).fetchone()[0]=='UNSUBSCRIBED'
            assert c.execute('SELECT lead_status FROM prospects WHERE id=?',(pid,)).fetchone()[0]=='DO_NOT_CONTACT'
            assert c.execute("SELECT COUNT(*) FROM activities WHERE prospect_id=? AND event_type IN ('EMAIL_SMTP_ACCEPTED','EMAIL_OPEN_SIGNAL','EMAIL_CLICK_SIGNAL','EMAIL_UNSUBSCRIBED')",(pid,)).fetchone()[0]>=4
            assert client.post('/api/tracking/u/'+tokens['u'],content='confirm=stop').status_code==200
            assert c.execute("SELECT COUNT(*) FROM email_engagement_events WHERE message_id=? AND event_type='UNSUBSCRIBED'",(result['id'],)).fetchone()[0]==1
    finally:app.dependency_overrides.clear()
