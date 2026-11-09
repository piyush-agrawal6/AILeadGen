from test_phase4 import workspace,payload
from app.mail import service
from app.mail.templates import seed,render_client_template


def test_production_formatted_redirect_is_persisted_without_claiming_contact(workspace):
    c,b,pid,config,transport=workspace
    config.mode='production';config.live_approved=True
    config.signature_name='PlaneByte';config.company='PlaneByte';config.from_address='planebyte@gmail.com'
    transport.health_check.return_value={'smtp':'READY','imap':'READY'}
    seed(c)
    rendered=render_client_template(c,b.id,'website',config)
    body=payload(c,pid);body.update(subject=rendered['rendered_subject'],body_text=rendered['rendered_body'],template_id='website',message_type='MANUAL_REPLY')
    body['preview_token']=service.preview(c,pid,'founder@example.com',body)['preview_token']
    result=service.send(c,pid,'founder@example.com',body,controlled_envelope_to='agrawaljoy1@gmail.com',controlled_authorization='owner-clean-start')
    message=transport.send_message.call_args[0][0]
    assert message['To']=='agrawaljoy1@gmail.com' and message['Subject']==rendered['rendered_subject']
    assert 'TEST MODE' not in message.get_body(preferencelist=('plain',)).get_content()
    assert 'PlaneByte' in message.get_body(preferencelist=('plain',)).get_content()
    assert 'contact@planebyte.com' in message.get_body(preferencelist=('plain',)).get_content()
    row=c.execute('SELECT * FROM email_messages WHERE id=?',(result['id'],)).fetchone()
    assert row['body_text']==rendered['rendered_body']
    assert row['test_mode']==1 and row['message_type']=='OWNER_CONTROLLED_REDIRECT'
    assert row['to_address']=='agrawaljoy1@gmail.com' and row['intended_to']=='public@hotel.example'
    assert c.execute('SELECT last_contact_at FROM prospect_sales WHERE prospect_id=?',(pid,)).fetchone()[0] is None
    assert c.execute('SELECT lead_status FROM prospects WHERE id=?',(pid,)).fetchone()[0]=='READY_TO_CONTACT'
    assert c.execute("SELECT COUNT(*) FROM activities WHERE event_type='OWNER_CONTROLLED_REDIRECT'").fetchone()[0]==1
    assert service.send(c,pid,'founder@example.com',body,controlled_envelope_to='agrawaljoy1@gmail.com',controlled_authorization='owner-clean-start')['duplicate_prevented']
    transport.send_message.assert_called_once()
