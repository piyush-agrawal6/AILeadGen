from app.mail.limits import MAX_PER_HOUR,MAX_PER_DAY,MIN_SPACING_SECONDS
"""Owner-editable targets in existing shared settings; environment switches stay authoritative."""
import json
from app.mail.config import mail_settings
from app.database.prospects import now

TARGET_FIELDS=('daily_qualified_lead_target','daily_email_target','max_hour','max_day','followup_days','automation_timezone')

def effective_settings(c,base=None):
    s=base or mail_settings()
    from app.api.organization import workspace_settings
    from app.platform.context import organization
    data=workspace_settings(c,organization()) or {}
    saved=data.get('automation',{})
    updates={key:saved[key] for key in TARGET_FIELDS if key in saved}
    updates['max_hour']=min(MAX_PER_HOUR,s.max_hour,int(updates.get('max_hour',s.max_hour)))
    updates['max_day']=min(MAX_PER_DAY,s.max_day,int(updates.get('max_day',s.max_day)))
    updates['daily_email_target']=min(updates['max_day'],int(updates.get('daily_email_target',s.daily_email_target)))
    foundation=data.get('foundation',{})
    sender=foundation.get('sender',{})
    for source,target in [('display_name','from_name'),('human_sender_name','outreach_sender_name'),('sender_role','outreach_sender_role'),('company','company'),('website','website')]:
        if source in sender:updates[target]=sender[source]
    return s.model_copy(update=updates)

def save_targets(c,values,actor):
    # Same transaction lock as existing settings saves prevents losing unrelated preferences.
    if getattr(c,'backend',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(691944520)')
    from app.api.organization import workspace_settings,save_workspace_settings
    from app.platform.context import organization
    org=organization();data=workspace_settings(c,org) or {}
    data['automation']=values
    save_workspace_settings(c,org,data,actor)
