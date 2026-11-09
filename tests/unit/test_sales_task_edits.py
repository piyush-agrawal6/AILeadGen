from datetime import datetime,timezone,timedelta
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from test_people import owned,seed
from app.platform.context import workspace_scope
from app.sales import tasks
from app.api.routes.tasks import Change


def test_owned_task_edit_reassign_priority_due_date_and_conflict_preserve_history(owned):
    c,_,org,other=owned
    with workspace_scope(c,'controlled@example.test',org):
        b=seed(c,org);created=tasks.create(c,tasks.Task(business_id=b.id,title='Review public company evidence',task_type='REVIEW',due_at='2026-12-01T09:00:00Z'))
        changed=Change(revision=1,title='Prepare next steps',priority='HIGH',due_at='2026-12-02T09:00:00+05:30',assigned_to='controlled@example.test',note='Owner-approved internal research')
        result=tasks.update(c,created['id'],changed.revision,changed.status,changed.model_dump(exclude={'revision','status'},exclude_unset=True))
        assert result['revision']==2 and result['priority']=='HIGH' and result['title']=='Prepare next steps'
        assert result['due_at']=='2026-12-02T03:30:00+00:00' and result['status']=='OPEN'
        with pytest.raises(HTTPException) as conflict:tasks.update(c,created['id'],1,changes={'title':'Stale edit'})
        assert conflict.value.status_code==409
        with pytest.raises(HTTPException):tasks.update(c,created['id'],2,changes={'assigned_to':'foreign@example.test'})
        assert tasks.get(c,created['id'])['revision']==2
        assert tasks.listing(c,priority='HIGH',view='MY')['total']==1
        assert tasks.listing(c,priority='LOW')['total']==0
        assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0
    with workspace_scope(c,'foreign@example.test',other):
        with pytest.raises(HTTPException):tasks.update(c,created['id'],2,changes={'title':'Foreign edit'})


def test_task_date_views_use_explicit_timezone_and_keep_other_workspace_private(owned):
    c,_,org,_=owned;present=datetime.now(timezone.utc)
    with workspace_scope(c,'controlled@example.test',org):
        b=seed(c,org)
        for title,date in [('Past',present-timedelta(days=2)),('Future',present+timedelta(days=3))]:tasks.create(c,tasks.Task(business_id=b.id,title=title,task_type='REVIEW',due_at=date.isoformat()))
        assert tasks.listing(c,view='OVERDUE',tz='Asia/Kolkata')['total']==1
        assert tasks.listing(c,view='UPCOMING',tz='Asia/Kolkata')['total']==1
        with pytest.raises(HTTPException):tasks.listing(c,view='TODAY',tz='Invalid/Timezone')
    for fields in ({'title':None},{'due_at':'2026-12-01'},{'priority':'URGENT'},{'assigned_to':'x'*255}):
        with pytest.raises(ValidationError):Change(revision=1,**fields)
