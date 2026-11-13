"""Measure a frozen, independently reviewed corpus without changing its labels.

Consumes saved real inference predictions. Does not call providers, approve
licenses, manufacture labels, or treat small/unauthorized samples as acceptance.
"""
import argparse
import json
import math
from collections import Counter,defaultdict
from pathlib import Path

HIGH={'Recommendation request','Seeking service provider','Product comparison','Alternative search','Explicit budget/timeline'}

def ratio(n,d):return n/d if d else None

def wilson(n,d):
    if not d:return None
    z=1.959963984540054;p=n/d;denominator=1+z*z/d
    center=(p+z*z/(2*d))/denominator
    margin=z*math.sqrt((p*(1-p)+z*z/(4*d))/d)/denominator
    return [max(0,center-margin),min(1,center+margin)]

def ndcg(rows,key,k=10):
    def dcg(ordered):return sum((2**row['relevance']-1)/math.log2(index+2) for index,row in enumerate(ordered[:k]))
    ranked=sorted(rows,key=lambda row:(-row[key],row['id']));ideal=dcg(sorted(rows,key=lambda row:(-row['relevance'],row['id'])))
    return ratio(dcg(ranked),ideal)

def evaluate(corpus,predictions,thresholds=None,*,_slices=True):
    cases=corpus['cases'];predicted={row['id']:row for row in predictions['items']}
    if len(predicted)!=len(predictions['items']) or set(predicted)!={row['id'] for row in cases}:raise ValueError('Predictions must cover the frozen corpus exactly once.')
    confusion=defaultdict(Counter);tp=fp=fn=tn=correct=grounded=quotes=high_score_fp=noncommercial=0;ranking=[];calibration=defaultdict(lambda:[0,0]);probability_errors=[]
    for case in cases:
        output=predicted[case['id']];expected=case['category'];actual=output['category']
        confusion[expected][actual]+=1;correct+=expected==actual
        expected_high=case['explicit_commercial'];actual_high=actual in HIGH
        tp+=expected_high and actual_high;fp+=not expected_high and actual_high;fn+=expected_high and not actual_high;tn+=not expected_high and not actual_high
        noncommercial+=not expected_high;high_score_fp+=not expected_high and output['score']>=75
        source=case['title']+'\n'+case['excerpt']
        for quote in output.get('quotes',[]):quotes+=1;grounded+=quote in source
        bucket=output.get('uncertainty','unknown');calibration[bucket][0]+=expected==actual;calibration[bucket][1]+=1
        if (probability:=output.get('explicit_commercial_probability')) is not None:
            if type(probability) not in (int,float) or not math.isfinite(probability) or not 0<=probability<=1:raise ValueError('Invalid reported probability; no inferred confidence allowed.')
            probability_errors.append((probability-int(expected_high))**2)
        ranking.append({'id':case['id'],'relevance':case['relevance'],'score':output['score'],'keyword_score':output['keyword_score']})
    precision=ratio(tp,tp+fp);recall=ratio(tp,tp+fn)
    metrics={'sample_size':len(cases),'category_accuracy':ratio(correct,len(cases)),'category_accuracy_wilson95':wilson(correct,len(cases)),'confusion_matrix':{key:dict(value) for key,value in sorted(confusion.items())},'explicit_intent':{'tp':tp,'fp':fp,'fn':fn,'tn':tn,'precision':precision,'recall':recall,'false_positive_rate':ratio(fp,fp+tn),'precision_wilson95':wilson(tp,tp+fp),'recall_wilson95':wilson(tp,tp+fn)},'high_score_false_positive_rate':ratio(high_score_fp,noncommercial),'high_score_false_positives':high_score_fp,'exact_quote_grounding':{'correct':grounded,'total':quotes,'rate':ratio(grounded,quotes),'limitation':'Exact attribution only; human review must validate interpretation and factual claims.'},'ndcg_at_10':ndcg(ranking,'score'),'keyword_ndcg_at_10':ndcg(ranking,'keyword_score'),'confidence_calibration':{'categorical_empirical_accuracy':{key:{'correct':value[0],'count':value[1],'accuracy':ratio(*value)} for key,value in calibration.items()},'brier_score':sum(probability_errors)/len(probability_errors) if probability_errors else None,'numeric_probability_count':len(probability_errors),'limitation':'Uncertainty labels and relevance scores are not purchase probabilities.'}}
    for name,key in (('precision_at_10','score'),('keyword_precision_at_10','keyword_score')):
        top=sorted(ranking,key=lambda row:(-row[key],row['id']))[:10]
        metrics[name]=ratio(sum(row['relevance']>=2 for row in top),len(top))
    if _slices:
        metrics['slices']={}
        for field in ('source_family','language','industry'):
            slices={}
            for value in sorted({row.get(field,'unknown') for row in cases}):
                selected=[row for row in cases if row.get(field,'unknown')==value]
                slices[value]=evaluate({'cases':selected},{'items':[predicted[row['id']] for row in selected]},_slices=False)['metrics']
            metrics['slices'][field]=slices
    blockers=[]
    if len(cases)<120:blockers.append('Independent protocol minimum of 120 cases not met.')
    if len({row.get('source_family') for row in cases})<3:blockers.append('Three approved source families required.')
    if len({row.get('industry') for row in cases})<4:blockers.append('Four industries required.')
    if any(row.get('permission_approved') is not True or len(set(row.get('independent_reviewers',[])))<2 or row.get('adjudicated') is not True for row in cases):blockers.append('Publisher permissions, two independent reviewers and adjudication required for every case.')
    if not thresholds or thresholds.get('owner_approved') is not True:blockers.append('Owner-approved frozen thresholds not supplied.')
    else:
        for key,value in thresholds.get('minimums',{}).items():
            actual=metrics.get(key)
            if type(actual) not in (int,float) or actual<value:blockers.append('Minimum gate failed: '+key)
        for key,value in thresholds.get('maximums',{}).items():
            actual=metrics.get(key)
            if type(actual) not in (int,float) or actual>value:blockers.append('Maximum gate failed: '+key)
    return {'version':'INTENT_INDEPENDENT_QUALITY_V1','status':'NOT_ACCEPTED' if blockers else 'METRIC_GATES_PASS_REVIEW_REQUIRED','metrics':metrics,'blockers':blockers,'source':'Saved predictions; no provider calls, no edited labels. Human grounding, cost, privacy and deployed acceptance remain separate gates.'}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--corpus',required=True,type=Path);parser.add_argument('--predictions',required=True,type=Path);parser.add_argument('--thresholds',type=Path)
    args=parser.parse_args();print(json.dumps(evaluate(json.loads(args.corpus.read_text()),json.loads(args.predictions.read_text()),json.loads(args.thresholds.read_text()) if args.thresholds else None),indent=2))
