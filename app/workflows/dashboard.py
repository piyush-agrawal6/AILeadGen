"""Read-only, workspace-scoped dashboard shared by API surfaces."""

def summary(c,organization=None):
 from app.platform.context import organization as active_organization
 organization=active_organization(organization)
 # Read-only dashboard. Workers own reconciliation; opening a page must not
 # rewrite every lead or compete with scan scoring transactions.
 counts={r['contact_state']:r['n'] for r in c.execute('SELECT contact_state,COUNT(*) n FROM master_lead_state WHERE organization_id=? GROUP BY contact_state',(organization,)).fetchall()}
 sales={r['sales_state']:r['n'] for r in c.execute('SELECT sales_state,COUNT(*) n FROM master_lead_state WHERE organization_id=? GROUP BY sales_state',(organization,)).fetchall()}
 return {'qualified':sum(counts.values()),'ready':counts.get('READY_TO_EMAIL',0)+counts.get('EMAIL_QUEUED',0),'queued':c.execute("SELECT COUNT(*) FROM outreach_run_items i JOIN workflow_runs r ON r.id=i.run_id WHERE r.organization_id=? AND r.status='RUNNING' AND i.status='READY'",(organization,)).fetchone()[0],
 'sent':c.execute("SELECT COUNT(*) FROM email_messages WHERE organization_id=? AND direction='OUTBOUND' AND status='SENT' AND test_mode=0",(organization,)).fetchone()[0], 'replies':counts.get('REPLIED',0),'manual':counts.get('MANUAL_CONTACT_REQUIRED',0),'meetings':sales.get('MEETING',0),'proposals':sales.get('PROPOSAL',0),'won':sales.get('WON',0),
 'active_runs':[dict(r) for r in c.execute("SELECT id,name,kind,status,requested,result_count,created_at,campaign_id FROM workflow_runs WHERE organization_id=? AND status IN ('RUNNING','PAUSED','PREPARING','NEEDS_REVIEW') ORDER BY created_at DESC LIMIT 10",(organization,)).fetchall()],
 'upcoming':[dict(r) for r in c.execute('SELECT id,name,kind,next_run_at,timezone FROM automation_schedules WHERE organization_id=? AND enabled=1 AND deleted_at IS NULL ORDER BY next_run_at LIMIT 5',(organization,)).fetchall()]}
