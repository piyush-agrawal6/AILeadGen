"""Quality arithmetic and gate integrity, not claims about production AI quality."""
import importlib.util
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('radar_quality',Path(__file__).resolve().parents[2]/'scripts/evaluate_intent_radar_quality.py')
quality=importlib.util.module_from_spec(spec);spec.loader.exec_module(quality)

def test_confusion_false_positive_grounding_and_small_set_denial():
    corpus={'cases':[{'id':'positive','title':'Need a supplier','excerpt':'','category':'Seeking service provider','explicit_commercial':True,'relevance':3},{'id':'negative','title':'Not buying anything','excerpt':'','category':'Explicitly non-buying','explicit_commercial':False,'relevance':0}]}
    predictions={'items':[{'id':'positive','category':'Seeking service provider','score':90,'keyword_score':10,'quotes':['Need a supplier']},{'id':'negative','category':'Recommendation request','score':80,'keyword_score':100,'quotes':['fabricated quote']}]}
    result=quality.evaluate(corpus,predictions)
    assert result['status']=='NOT_ACCEPTED'
    assert result['metrics']['explicit_intent']=={'tp':1,'fp':1,'fn':0,'tn':0,'precision':.5,'recall':1.0,'false_positive_rate':1.0,'precision_wilson95':quality.wilson(1,2),'recall_wilson95':quality.wilson(1,1)}
    assert result['metrics']['exact_quote_grounding']['rate']==.5
    assert result['metrics']['ndcg_at_10']==1 and result['metrics']['keyword_ndcg_at_10']<1
    assert result['metrics']['confidence_calibration']['brier_score'] is None
    assert result['metrics']['confusion_matrix']['Explicitly non-buying']['Recommendation request']==1

def test_missing_or_duplicate_predictions_cannot_manufacture_coverage():
    with pytest.raises(ValueError):quality.evaluate({'cases':[{'id':'a'}]},{'items':[]})
    with pytest.raises(ValueError):quality.evaluate({'cases':[{'id':'a'}]},{'items':[{'id':'a'},{'id':'a'}]})
