from copy import deepcopy
import pytest
from app.reports.metrics import client_metrics,HEADER_CHECKS


def sample():
    return {'mode':'REACHABLE','website':{'https_enabled':True},'lighthouse':{'performance_score':13,'seo_score':75},'scores':{'WEBSITE':62,'SEO':97,'SECURITY':48},'evidence':{'SECURITY':[{'code':code} for _,code in HEADER_CHECKS]}}


def test_client_scores_are_measured_quality_not_sales_scores():
    data=sample();metrics=client_metrics(data)
    assert metrics['WEBSITE']['current']==13 and metrics['WEBSITE']['target']==90 and metrics['WEBSITE']['increase']==77
    assert metrics['SEO']['current']==75 and metrics['SEO']['target']==100 and metrics['SEO']['increase']==25
    assert metrics['SECURITY']['current']==14 and metrics['SECURITY']['increase']==86
    assert metrics['SECURITY']['passed']==1 and metrics['SECURITY']['assessed']==7
    assert data['scores']=={'WEBSITE':62,'SEO':97,'SECURITY':48}


def test_absent_security_findings_never_imply_passing_headers():
    data=sample();data['evidence']['SECURITY']=[]
    metrics=client_metrics(data)
    assert metrics['SECURITY']['current'] is None and metrics['SECURITY']['increase'] is None
    assert metrics['SECURITY']['assessed']==1


@pytest.mark.parametrize('mode',['NO_WEBSITE','UNREACHABLE','UNASSESSED'])
def test_missing_baselines_do_not_become_zero_or_opportunity_scores(mode):
    data=sample();data['mode']=mode
    assert all(metric['current'] is None and metric['target'] is None and metric['increase'] is None for metric in client_metrics(data).values())


def test_existing_good_performance_is_never_given_a_lower_goal():
    data=sample();data['lighthouse']['performance_score']=98
    assert client_metrics(data)['WEBSITE']['target']==98
    assert client_metrics(data)['WEBSITE']['increase']==0


def test_explicit_check_results_and_configured_targets_are_supported():
    data=sample();data['evidence']['SECURITY']=[];data['website']['security_checks']={code:True for _,code in HEADER_CHECKS};data['brand']={'score_targets':{'WEBSITE':95,'SEO':95,'SECURITY':100}}
    before=deepcopy(data);metrics=client_metrics(data)
    assert metrics['SECURITY']['current']==100 and metrics['SECURITY']['increase']==0
    assert metrics['WEBSITE']['target']==95 and metrics['SEO']['increase']==20
    assert data==before


@pytest.mark.parametrize('value',[None,True,-1,101,float('nan'),float('inf')])
def test_invalid_measurements_are_unassessed(value):
    data=sample();data['lighthouse']['performance_score']=value
    assert client_metrics(data)['WEBSITE']['current'] is None
