"""Synthetic tests verify tooling, never serve as independent human evidence."""
import copy
import pytest
from app.growth_intelligence import evaluation as e
from scripts.evaluate_intent_radar_quality import evaluate,wilson

def example():
    registration={'sampling_seed':'synthetic-test-only','source_windows':{'controlled':{'from':'2026-01-01T00:00:00Z','to':'2026-02-01T00:00:00Z'}},'protocol_approved_at':'2026-01-01','implementation_authors':['implementation-test-author'],'reviewer_ids':['reviewer-a-test-only','reviewer-b-test-only'],'adjudicator_id':'adjudicator-test-only'}
    cases=[{'id':'synthetic-'+str(i),'title':'Synthetic tool case '+str(i),'excerpt':'We need a supplier for this controlled example '+str(i),'source_url':'https://example.test/'+str(i),'source_family':'controlled','language':'en','industry':'Synthetic industry','stratum':s,'observed_at':'2026-01-02T00:00:00Z','retrieved_at':'2026-01-03T00:00:00Z','permission_reference':'Synthetic fixture; not independent evidence','permission_approved':True,'icps':[{'id':'controlled-profile','description':'Controlled supplier'}],'prediction':'MUST NOT LEAK'} for i,s in enumerate(e.STRATA)]
    package=e.prepare(cases,registration)
    labels=[{'id':case['id'],'category':'Seeking service provider','explicit_commercial':True,'relevance':3,'industry':'Synthetic industry','industry_relevant':True,'icp_fit':{'controlled-profile':'SUPPORTED'},'commercial_evidence':'We need a supplier','contradictory_evidence':'','uncertainty':'Low','supported_claims':['We need a supplier'],'rationale':'Controlled synthetic test rationale only.'} for case in package['cases']]
    reviews=[{'package_hash':package['package_hash'],'reviewer_id':r,'independent_attestation':True,'model_outputs_not_seen':True,'labels':copy.deepcopy(labels)} for r in registration['reviewer_ids']]
    return package,reviews

def test_blind_package_excludes_predictions_and_never_claims_small_set_pass():
    package,reviews=example()
    assert package['readiness']['status']=='NOT_READY' and package['readiness']['cases']==6
    assert all('prediction' not in case and 'stratum' not in case and 'industry' not in case for case in e.blind_rows(package))
    assert e.validate_review(package,reviews[0]).reviewer_id=='reviewer-a-test-only'
    changed=copy.deepcopy(package);changed['cases'][0]['excerpt']='Changed'
    with pytest.raises(ValueError):e.verify(changed)

def test_independence_missing_ids_and_invented_evidence_are_rejected():
    package,reviews=example()
    for bad in (dict(reviews[0],reviewer_id='implementation-test-author'),dict(reviews[0],labels=reviews[0]['labels'][:-1])):
        with pytest.raises(ValueError):e.validate_review(package,bad)
    bad=copy.deepcopy(reviews[0]);bad['labels'][0]['commercial_evidence']='Fabricated claim'
    with pytest.raises(ValueError):e.validate_review(package,bad)
    with pytest.raises(ValueError):e.adjudication_queue(package,[reviews[0],reviews[0]])

def test_disagreements_require_actual_third_reviewer_and_all_resolutions():
    package,reviews=example();reviews[1]['labels'][0]['relevance']=0
    queue=e.adjudication_queue(package,reviews)
    assert queue['agreement_count']==5 and len(queue['disputes'])==1
    decision={'package_hash':package['package_hash'],'adjudicator_id':'reviewer-a-test-only','all_cases_reviewed':True,'provenance_verified':True,'resolutions':[]}
    with pytest.raises(ValueError):e.finalize(package,reviews,decision)
    decision['adjudicator_id']='adjudicator-test-only'
    with pytest.raises(ValueError):e.finalize(package,reviews,decision)
    decision['resolutions']=[{'id':reviews[0]['labels'][0]['id'],'label':reviews[0]['labels'][0],'reason':'Controlled synthetic resolution reason.'}]
    corpus=e.finalize(package,reviews,decision)
    assert corpus['status']=='LABELS_FINALIZED_NOT_QUALITY_ACCEPTED'
    predictions={'items':[{'id':c['id'],'category':c['category'],'score':90,'keyword_score':10,'quotes':['We need a supplier'],'icp_fit':c['icp_fit'],'generation_mode':'AI','latency_seconds':1} for c in corpus['cases']]}
    assessment={'adjudicator_id':'adjudicator-test-only','provenance_verified':True,'package_hash':package['package_hash'],'predictions_hash':e.digest(predictions),'cases':[{'id':c['id'],'unsupported_claims':0,'claims_reviewed':1,'invented_sensitive_claims':0,'cross_workspace_contamination':0,'injection_side_effects':0} for c in corpus['cases']]}
    result=e.score(package,corpus,predictions,assessment,evaluate,wilson)
    assert result['status']=='NOT_ACCEPTED'
    assert result['gates']['high_intent_precision']['actual']==1
    assert not result['gates']['honest_bounded_fallback_rate']['pass']
    assert result['gates']['exact_attribution']['pass']
    assert result['blockers'] # A perfect authored fixture is never independent acceptance.

def test_unapproved_sources_and_outside_windows_are_not_sampled():
    package,_=example();candidates=copy.deepcopy(package['cases'])
    for c in candidates:c['observed_at']='2025-01-01T00:00:00Z'
    assert e.prepare(candidates,package['registration'])['readiness']['cases']==0
