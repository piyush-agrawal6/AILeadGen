"""Evidence admission, separate from relevance score and purchasing certainty.

A topic match or general discussion alone is not an opportunity. This bounded
rule can explain a review candidate; independent quality evaluation is separate.
"""
import re
VERSION='OPPORTUNITY_EVIDENCE_V1'
NEGATIVE=re.compile(r"\b(?:not (?:looking to )?(?:buy|purchase|hire)|no (?:purchase|buying) plans|(?:don['’]t|do not) (?:need|want) (?:to buy|to purchase|a vendor)|not looking for|(?:looking for|seeking|need) feedback|research participants|homework|tutorial|assignment|we are hiring|job opening)\b",re.I)
REQUEST=re.compile(r"\b(?:(?:i|we)\s+(?:am\s+|are\s+)?(?:looking for|seeking|need|want|evaluating|comparing)|looking for|seeking|any recommendations for|can anyone recommend|which (?:tool|service|provider|software)|(?:i|we)\s+(?:plan|intend)\s+to\s+(?:buy|purchase|hire))\b[^.!?\n]{0,160}",re.I)
OBJECT=re.compile(r'\b(tool|software|platform|provider|vendor|service|agency|consultant|solution|partner|contractor|alternative|replacement|product|system|company|companies|engineer|developer)\b',re.I)

def assess(signal):
    source=(signal.get('title','')+'\n'+signal.get('excerpt',''));evidence=signal.get('evidence') or {};ranking=signal.get('ranking') or {}
    reasons=[];quote=None
    if not signal.get('available'):reasons.append('Current source evidence is unavailable or expired.')
    if NEGATIVE.search(source) or evidence.get('penalties') or ranking.get('excluded') or ranking.get('scoring',{}).get('dimensions',{}).get('contradictory_evidence',0)<0:
        reasons.append('Negative or noncommercial evidence requires review before promotion.')
    for match in REQUEST.finditer(source):
        if OBJECT.search(match.group()) or re.search(r'\b(?:evaluating|comparing|buy|purchase|hire)\b',match.group(),re.I):quote=match.group().strip();break
    if not quote:reasons.append('No explicit request, evaluation, replacement or purchase consideration is evidenced.')
    aligned=bool(evidence.get('matched_keywords') or evidence.get('matched_topics') or ranking.get('scoring',{}).get('dimensions',{}).get('problem_service_fit',0))
    if not aligned:reasons.append('No alignment to requested topics or reviewed service/ICP context is recorded.')
    return {'policy_version':VERSION,'eligible':not reasons,'intent_quote':quote,'reasons':reasons,
        'basis':'Observed request plus recorded targeting alignment; not a verified buyer, contact, budget or purchasing event.',
        'next_step':'Review the original request and unknowns.' if not reasons else 'Keep as a signal or saved research; collect/review evidence before promoting.'}
