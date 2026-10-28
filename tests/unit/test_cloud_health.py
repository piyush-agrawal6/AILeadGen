import json
from io import BytesIO
from unittest.mock import Mock
import pytest
from app.cloud_doctor import completed_canary,overpass_health
from app.database.connection import db_session
from app.database.migrations import run_migrations


@pytest.mark.parametrize('matching_image,completed,expected',[(True,True,True),(False,True,False),(True,False,False)])
def test_canary_readiness_requires_current_image_and_completed_execution(monkeypatch,matching_image,completed,expected):
    with db_session() as conn:
        run_migrations(conn)
        conn.execute("INSERT INTO artifact_objects(object_key,kind,content_type,created_at) VALUES('audits/canary/example/result.json','worker_canary','application/json','2026-10-25')")
    report={'status':'passed','image':'current' if matching_image else 'old','execution':'worker-canary','lighthouse':True}
    storage=Mock();storage.get.return_value=BytesIO(json.dumps(report).encode())
    monkeypatch.setattr('app.storage.R2ArtifactStorage',lambda:storage)
    session=Mock();session.get.return_value.status_code=200
    session.get.return_value.json.return_value={'completionTime':'2026-10-25','succeededCount':1} if completed else {'runningCount':1}
    job={'name':'projects/test/locations/region/jobs/worker','template':{'template':{'containers':[{'image':'current'}]}}}
    assert bool(completed_canary(job,session)) is expected


def test_overpass_checks_only_one_fallback_and_reports_degradation(monkeypatch):
    check=Mock(side_effect=[{'status':'warning'},{'status':'ready'}]);monkeypatch.setattr('app.cloud_doctor.source_health',check)
    result=overpass_health()
    assert result['status']=='ready' and 'fallback' in result['details']
    assert check.call_count==2
