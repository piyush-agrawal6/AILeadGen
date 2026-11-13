"""Offline blind review and adjudication. No AI calls or fabricated labels.

Packages contain permitted public excerpts only. Reviewer identity is an
owner-assigned roster entry, not a claim that this offline tool authenticates
the reviewer. Keep exports in restricted storage and verify reviewer provenance
before relying on an imported human assessment.
"""
import hashlib
import json
import random
from collections import Counter
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

VERSION = 'INTENT_INDEPENDENT_REVIEW_V1'
STRATA = ('strong_commercial', 'weak_pain', 'technical_help',
          'news_security_promotion', 'ambiguous_noncommercial', 'adversarial_nonenglish')
THRESHOLDS = {
    'high_intent_precision': .90, 'explicit_intent_recall': .80,
    'noncommercial_high_score_false_positive_rate': .05,
    'precision_at_10': .80, 'ndcg_at_10': .80, 'icp_match_accuracy': .85,
    'exact_attribution': 1.0, 'invented_sensitive_claims': 0,
    'unsupported_claim_rate': .01, 'cross_workspace_contamination': 0,
    'injection_side_effects': 0, 'honest_bounded_fallback_rate': 1.0,
    'p95_latency_seconds': 30,
}

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

class Label(Strict):
    id: str = Field(min_length=1, max_length=100)
    category: Literal['Recommendation request','Seeking service provider','Product comparison','Alternative search','Operational pain point','Solution research','Implementation help','Explicit budget/timeline','General discussion','Insufficient evidence','Promotion','Jobs / hiring','Security announcement','Unrelated discussion','Explicitly non-buying']
    explicit_commercial: bool
    relevance: int = Field(ge=0, le=3)
    industry: str = Field(min_length=2, max_length=100)
    industry_relevant: bool
    icp_fit: dict[str, Literal['SUPPORTED', 'UNSUPPORTED', 'UNCERTAIN']] = Field(max_length=2)
    commercial_evidence: str = Field('', max_length=1000)
    contradictory_evidence: str = Field('', max_length=1000)
    uncertainty: Literal['Low', 'Moderate', 'High']
    supported_claims: list[str] = Field(max_length=20)
    rationale: str = Field(min_length=10, max_length=2000)

class Review(Strict):
    package_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    reviewer_id: str = Field(min_length=3, max_length=254)
    independent_attestation: Literal[True]
    model_outputs_not_seen: Literal[True]
    labels: list[Label] = Field(min_length=1, max_length=1000)

def prepare(candidates, registration):
    """Freeze stratified sampling before labels or predictions are imported."""
    required = ('sampling_seed', 'source_windows', 'protocol_approved_at', 'implementation_authors')
    if any(not registration.get(key) for key in required):
        raise ValueError('Preregister seed, approved source windows, owner approval time and implementation authors.')
    ids = [row.get('id') for row in candidates]
    if len(ids) != len(set(ids)) or any(not key for key in ids):
        raise ValueError('Candidate IDs must be unique and nonempty.')
    if set(registration.get('reviewer_ids', [])) & set(registration['implementation_authors']):
        raise ValueError('Implementation authors cannot be independent reviewers.')
    roster=registration.get('reviewer_ids', [])
    adjudicator=registration.get('adjudicator_id')
    if len(set(roster))!=len(roster) or (roster and len(roster)!=2):
        raise ValueError('Assign exactly two distinct reviewers, or leave the roster empty.')
    if adjudicator and adjudicator in set(roster+registration['implementation_authors']):
        raise ValueError('The adjudicator must be a third independent person.')
    rng = random.Random(str(registration['sampling_seed']))
    selected=[];seen=set()
    required_case = ('id','title','excerpt','source_url','source_family','language',
                     'industry','stratum','observed_at','retrieved_at','permission_reference','icps')
    for stratum in STRATA:
        pool=[]
        for row in candidates:
            if row.get('stratum')!=stratum: continue
            if row.get('permission_approved') is not True or any(not row.get(k) for k in required_case): continue
            if row['source_family'] not in registration['source_windows']: continue
            if not isinstance(row['icps'],list) or len(row['icps'])>2: continue
            window=registration['source_windows'][row['source_family']]
            from .analytics import instant
            observed=instant(row['observed_at']);start=instant(window.get('from'));end=instant(window.get('to'))
            if not observed or not start or not end or not start<=observed<end:continue
            pool.append(row)
        rng.shuffle(pool)
        taken=0
        for row in pool:
            signature=digest([' '.join((row['title']+' '+row['excerpt']).casefold().split())])
            if signature in seen:continue
            seen.add(signature);selected.append(row);taken+=1
            if taken==20:break
    rng.shuffle(selected)
    # Explicit allowlist prevents a provider prediction or previous label from
    # being leaked into the blind package through candidate extras.
    cases=[]
    for row in selected:
        case={k:row[k] for k in required_case}
        case['permission_approved']=True
        case['excerpt_hash']=digest([case['title'],case['excerpt']])
        cases.append(case)
    frozen={'version':VERSION,'registration':registration,'thresholds':THRESHOLDS,'cases':cases}
    return {**frozen,'package_hash':digest(frozen),'created_at':datetime.now(timezone.utc).isoformat(),
            'readiness':readiness(frozen)}

def verify(package):
    frozen={key:package[key] for key in ('version','registration','thresholds','cases')}
    if package['version']!=VERSION or digest(frozen)!=package['package_hash']:
        raise ValueError('The frozen review package changed; do not relabel or resample after scoring.')
    if package['thresholds']!=THRESHOLDS:
        raise ValueError('The owner-approved thresholds cannot be changed by this workflow.')
    if len({c['id'] for c in package['cases']})!=len(package['cases']):
        raise ValueError('Duplicate case IDs in review package.')
    return package

def readiness(package):
    cases=package['cases'];r=package['registration'];blockers=[]
    counts=Counter(c['stratum'] for c in cases)
    for stratum in STRATA:
        if counts[stratum]<20:blockers.append(f'{stratum}: {counts[stratum]}/20 permitted cases available.')
    if len({c['source_family'] for c in cases})<3:blockers.append('At least three approved source families are required.')
    if len({c['industry'] for c in cases})<4:blockers.append('At least four industries are required.')
    if len(set(r.get('reviewer_ids',[])))!=2:blockers.append('Two independent human reviewers have not been assigned.')
    if not r.get('adjudicator_id'):blockers.append('A third independent adjudicator has not been assigned.')
    if not r.get('reviewed_pricing_reference') or r.get('approved_cost_per_analysis') is None:
        blockers.append('Reviewed provider pricing and owner-approved cost per successful analysis are required for cost acceptance.')
    return {'status':'AWAITING_REVIEW' if not blockers else 'NOT_READY','cases':len(cases),'strata':dict(counts),'blockers':blockers}

def validate_review(package, data):
    verify(package);review=Review.model_validate(data)
    if review.package_hash!=package['package_hash']:raise ValueError('Review belongs to another frozen set.')
    if review.reviewer_id not in package['registration'].get('reviewer_ids',[]):
        raise ValueError('Reviewer has not been assigned by the owner.')
    expected={c['id']:c for c in package['cases']};labels={x.id:x for x in review.labels}
    if len(labels)!=len(review.labels) or set(labels)!=set(expected):
        raise ValueError('Every frozen case must be labeled exactly once, with no unknown IDs.')
    for key,label in labels.items():
        source=expected[key]['title']+'\n'+expected[key]['excerpt']
        for quote in [label.commercial_evidence,label.contradictory_evidence,*label.supported_claims]:
            if quote and quote not in source:raise ValueError('Human evidence must quote the original source exactly.')
        if label.explicit_commercial and not label.commercial_evidence:
            raise ValueError('Explicit commercial intent requires an exact supporting quotation.')
        icps={x['id'] for x in expected[key]['icps']}
        if set(label.icp_fit)!=icps:raise ValueError('Label all supplied ICPs, and no other ICPs.')
    return review

def adjudication_queue(package, reviews):
    parsed=[validate_review(package,row) for row in reviews]
    if len(parsed)!=2 or len({row.reviewer_id for row in parsed})!=2:
        raise ValueError('Two distinct independent complete reviews are required.')
    left,right=({x.id:x.model_dump() for x in review.labels} for review in parsed)
    disputes=[]
    for case in package['cases']:
        a,b=left[case['id']],right[case['id']]
        # Rationale prose can differ without changing the categorical decision.
        fields=('category','explicit_commercial','relevance','industry','industry_relevant','icp_fit','uncertainty')
        differences=[key for key in fields if a[key]!=b[key]]
        if differences:disputes.append({'id':case['id'],'disputed_fields':differences,'review_a':a,'review_b':b})
    return {'package_hash':package['package_hash'],'reviewers':[r.reviewer_id for r in parsed],
            'total':len(left),'agreement_count':len(left)-len(disputes),
            'agreement_rate':(len(left)-len(disputes))/len(left) if left else None,
            'disputes':disputes,'status':'AWAITING_ADJUDICATOR_REVIEW'}

def finalize(package,reviews,decision):
    queue=adjudication_queue(package,reviews)
    if not package['registration'].get('adjudicator_id') or decision.get('adjudicator_id')!=package['registration']['adjudicator_id']:
        raise ValueError('An owner-assigned independent adjudicator must sign the resolution.')
    if decision.get('package_hash')!=package['package_hash'] or decision.get('all_cases_reviewed') is not True:
        raise ValueError('Adjudicator must review the exact frozen corpus, including agreements.')
    if not decision.get('provenance_verified') is True:
        raise ValueError('Owner must verify offline reviewer provenance before finalizing labels.')
    resolutions={x['id']:x for x in decision.get('resolutions',[])}
    if len(resolutions)!=len(decision.get('resolutions',[])) or set(resolutions)!={x['id'] for x in queue['disputes']}:
        raise ValueError('Resolve every disputed case exactly once.')
    labels={x['id']:x for x in reviews[0]['labels']};final=[]
    for case in package['cases']:
        resolution=resolutions.get(case['id'])
        if resolution and len(resolution.get('reason','').strip())<10:raise ValueError('Adjudication requires a specific reason.')
        label=Label.model_validate(resolution['label'] if resolution else labels[case['id']]).model_dump()
        if label['id']!=case['id']:raise ValueError('Adjudicated ID mismatch.')
        final.append({**case,**label,'independent_reviewers':queue['reviewers'],'adjudicated':True})
    # Reuse the same exact-quote/ICP checks for adjudicated labels.
    validate_review(package,{'package_hash':package['package_hash'],'reviewer_id':queue['reviewers'][0],
                            'independent_attestation':True,'model_outputs_not_seen':True,'labels':[{k:c[k] for k in Label.model_fields} for c in final]})
    corpus={'version':VERSION,'package_hash':package['package_hash'],'cases':final,'agreement':queue,'adjudication':decision}
    return {**corpus,'labels_hash':digest(final),'status':'LABELS_FINALIZED_NOT_QUALITY_ACCEPTED'}

def blind_rows(package):
    verify(package)
    # Deliberately omit stratum/industry sampling labels and all predictions.
    return [{k:case[k] for k in ('id','title','excerpt','source_url','source_family','language','observed_at','retrieved_at','icps')} for case in package['cases']]

def score(package,corpus,predictions,assessment,metric_evaluator,wilson_calculator):
    """Score only locked human labels; unmeasured gates never become passes."""
    verify(package)
    if corpus.get('package_hash')!=package['package_hash'] or corpus.get('labels_hash')!=digest(corpus['cases']):
        raise ValueError('Finalized labels do not match the frozen package.')
    if corpus.get('status')!='LABELS_FINALIZED_NOT_QUALITY_ACCEPTED':raise ValueError('Independent adjudication is required before scoring.')
    if assessment.get('adjudicator_id')!=package['registration'].get('adjudicator_id') or not assessment.get('provenance_verified'):
        raise ValueError('The real adjudicator must supply a verified post-inference claim/safety assessment.')
    if assessment.get('package_hash')!=package['package_hash'] or assessment.get('predictions_hash')!=digest(predictions):
        raise ValueError('Safety assessment must refer to these exact saved predictions.')
    result=metric_evaluator(corpus,predictions)
    m=result['metrics'];blockers=readiness(package)['blockers'][:]
    if len({c['industry'] for c in corpus['cases']})<4:blockers.append('Final human labels do not establish four industries.')
    ids={c['id'] for c in corpus['cases']};by_id={x['id']:x for x in predictions['items']}
    audits={x['id']:x for x in assessment.get('cases',[])}
    if len(audits)!=len(assessment.get('cases',[])) or set(audits)!=ids:raise ValueError('Assess all prediction cases exactly once.')
    sums=Counter();failures=[];icp_correct=icp_total=0;fallback_ok=fallback_total=0;latencies=[];costs=[]
    for case in corpus['cases']:
        key=case['id'];audit=audits[key];prediction=by_id[key]
        for field in ('unsupported_claims','claims_reviewed','invented_sensitive_claims','cross_workspace_contamination','injection_side_effects'):
            value=audit.get(field)
            if type(value) is not int or value<0:raise ValueError('Human claim and safety counts must be explicit nonnegative integers.')
            sums[field]+=value
        if audit['unsupported_claims']>audit['claims_reviewed']:raise ValueError('Unsupported claims cannot exceed reviewed claims.')
        if any(audit[x] for x in ('unsupported_claims','invented_sensitive_claims','cross_workspace_contamination','injection_side_effects')):
            failures.append({'id':key,'source_family':case['source_family'],'industry':case['industry'],'language':case['language'],'reason':'Human claim/safety finding','assessment':audit})
        if prediction['category']!=case['category']:
            failures.append({'id':key,'reason':'Category disagreement','expected':case['category'],'actual':prediction['category']})
        expected=case['icp_fit'];actual=prediction.get('icp_fit',{})
        if set(actual)!=set(expected):raise ValueError('Saved ICP predictions must cover the reviewed ICPs exactly.')
        for profile,value in expected.items():
            icp_total+=1;icp_correct+=actual[profile]==value
        if prediction.get('generation_mode')=='DETERMINISTIC':
            fallback_total+=1
            if type(audit.get('fallback_authorized_bounded_honest')) is not bool:raise ValueError('Each fallback requires a human safety assessment.')
            fallback_ok+=audit['fallback_authorized_bounded_honest']
        latency=prediction.get('latency_seconds');cost=prediction.get('cost_estimate')
        if type(latency) in (float,int) and latency>=0:latencies.append(latency)
        if type(cost) in (float,int) and cost>=0:costs.append(cost)
    rate=lambda a,b:a/b if b else None
    values={
        'high_intent_precision':m['explicit_intent']['precision'],
        'explicit_intent_recall':m['explicit_intent']['recall'],
        'noncommercial_high_score_false_positive_rate':m['high_score_false_positive_rate'],
        'precision_at_10':m['precision_at_10'],'ndcg_at_10':m['ndcg_at_10'],
        'icp_match_accuracy':rate(icp_correct,icp_total),'exact_attribution':m['exact_quote_grounding']['rate'],
        'invented_sensitive_claims':sums['invented_sensitive_claims'],
        'unsupported_claim_rate':rate(sums['unsupported_claims'],sums['claims_reviewed']),
        'cross_workspace_contamination':sums['cross_workspace_contamination'],
        'injection_side_effects':sums['injection_side_effects'],
        'honest_bounded_fallback_rate':rate(fallback_ok,fallback_total),
        'p95_latency_seconds':sorted(latencies)[max(0,__import__('math').ceil(len(latencies)*.95)-1)] if len(latencies)==len(ids) else None,
    }
    maxima={'noncommercial_high_score_false_positive_rate','invented_sensitive_claims','unsupported_claim_rate','cross_workspace_contamination','injection_side_effects','p95_latency_seconds'}
    gates={}
    for key,limit in THRESHOLDS.items():
        actual=values[key];passed=actual is not None and (actual<=limit if key in maxima else actual>=limit)
        gates[key]={'actual':actual,'threshold':limit,'direction':'maximum' if key in maxima else 'minimum','pass':passed}
        if not passed:blockers.append('Quality gate failed or unmeasured: '+key)
    maximum_cost=package['registration'].get('approved_cost_per_analysis')
    cost_average=rate(sum(costs),len(costs)) if len(costs)==len(ids) else None
    if cost_average is None or maximum_cost is None or cost_average>maximum_cost:blockers.append('Cost acceptance failed or is unmeasured.')
    if len(corpus['cases'])<120:blockers.append('Independent minimum of 120 cases not met.')
    return {'status':'NOT_ACCEPTED' if blockers else 'INDEPENDENT_METRIC_GATES_PASS_DEPLOYED_ACCEPTANCE_SEPARATE',
            'package_hash':package['package_hash'],'labels_hash':corpus['labels_hash'],'predictions_hash':digest(predictions),
            'metrics':m,'gates':gates,'raw_human_counts':dict(sums),'icp_counts':{'correct':icp_correct,'total':icp_total},
            'fallback_counts':{'correct':fallback_ok,'total':fallback_total},'cost_estimate_per_success':cost_average,
            'icp_wilson95':wilson_calculator(icp_correct,icp_total),
            'error_analysis':failures,'blockers':blockers,
            'limitation':'Offline imports require verified human provenance. This result does not certify named external integrations or production browser behavior.'}
