import json
import uuid
import pytest
from fastapi import HTTPException
from test_people import owned,seed
from app.platform.context import workspace_scope
from app.icp import service,discovery
from app.icp.models import Create,Update
from app.api.routes.workflows import Run
from app.workflows import service as workflows
from app.prospecting.intake import resolve_profile
from app.icp.matching import evaluate


def test_discovery_translates_supported_filters_and_freezes_owned_icp_revision(owned):
    c,_,org,other=owned
    with workspace_scope(c,'controlled@example.test',org):
        profile=service.create(c,Create(name='Dental teams',status='ACTIVE',criteria={'company':{'industries':['Dentistry'],'countries':['GB'],'regions':['Greater London'],'employee_min':10},'contact':{'job_titles':['Owner']}},request_id=uuid.uuid4()))
        preview=discovery.preview(c,profile['id'])
        assert preview['filters']['countries']==['United Kingdom'] and preview['filters']['verticals']==['dentists']
        assert preview['filters']['search_criteria']['employee_min']==10
        assert 'contact.job_titles' in [item['field'] for item in preview['post_discovery']]
        body=Run(kind='SCAN',icp_id=profile['id']).model_dump(mode='json')
        run=workflows.create(c,body,'controlled@example.test');c.commit()
        snapshot=json.loads(run['configuration_json'])['icp_snapshot'];assert snapshot['revision']==1
        assert workflows.create(c,body,'controlled@example.test')['id']==run['id']
        fields={key:profile[key] for key in ('name','description','status','criteria','revision')};fields['name']='Updated profile'
        service.update(c,profile['id'],Update(**fields));c.commit()
        assert resolve_profile(c,json.loads(run['configuration_json']))['revision']==1
        assert workflows.create(c,body,'controlled@example.test')['id']==run['id']
        b=seed(c,org);b.country='United Kingdom';b.vertical='dentistry'
        assert next(item for item in evaluate(profile,b,{})['criteria'] if item['field']=='company.countries')['status']=='MATCH'
        assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0
    with workspace_scope(c,'foreign@example.test',other):
        with pytest.raises(HTTPException):discovery.preview(c,profile['id'])
        with pytest.raises(HTTPException):resolve_profile(c,{'icp_snapshot':snapshot})


def test_custom_industry_never_silently_uses_unrelated_maps_category(owned):
    c,_,org,_=owned
    with workspace_scope(c,'controlled@example.test',org):
        profile=service.create(c,Create(name='Software businesses',status='ACTIVE',criteria={'company':{'industries':['Software'],'countries':['DE']}},request_id=uuid.uuid4()))
        preview=discovery.preview(c,profile['id'])
        assert preview['filters']['verticals']==[] and preview['warnings']
        assert preview['filters']['countries']==['Germany']
        assert c.execute('SELECT COUNT(*) FROM workflow_runs').fetchone()[0]==0
