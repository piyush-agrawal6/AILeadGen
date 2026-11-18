"""Evidence admission, separate from relevance score and purchasing certainty.

A topic match or general discussion alone is not an opportunity. This bounded
rule can explain a review candidate; independent quality evaluation is separate.
"""
import re
VERSION='OPPORTUNITY_EVIDENCE_V2'
NEGATIVE=re.compile(r"\b(?:not (?:looking to )?(?:buy|purchase|hire)|no (?:purchase|buying) plans|(?:don['’]t|do not) (?:need|want) (?:to buy|to purchase|a vendor)|not looking for|(?:looking for|seeking|need) feedback|research participants|homework|tutorial|assignment|we are hiring|job opening)\b",re.I)
REQUEST=re.compile(r"\b(?:(?:i|we)\s+(?:am\s+|are\s+)?(?:looking for|seeking|need|want|evaluating|comparing|replacing|migrating from)|looking for|seeking|any recommendations?(?: for)?|any suggestions?(?: for)?|can anyone recommend|recommend(?:ations?)?\s+(?:for|a|an)|alternative(?:s)?\s+to|instead of|replace our|migrating from|which (?:tool|service|provider|software|platform)|what(?:'s| is)\s+the\s+best|(?:i|we)\s+(?:plan|intend)\s+to\s+(?:buy|purchase|hire))\b[^.!?\n]{0,160}",re.I)
OBJECT=re.compile(r'\b(tool|software|platform|provider|vendor|service|agency|consultant|solution|partner|contractor|alternative|replacement|product|system|company|companies|engineer|developer|crm|saas|stack|database|api|app|framework)\b',re.I)

def assess(signal):
    source=(signal.get('title','')+'\n'+signal.get('excerpt',''));evidence=signal.get('evidence') or {};ranking=signal.get('ranking') or {}
    provenance=evidence.get('provenance') or {}
    reasons=[];quote=None
    if not signal.get('available'):
        reasons.append('Current source evidence is unavailable or expired.')
        return {'policy_version':VERSION,'eligible':False,'intent_quote':None,'reasons':reasons,
            'basis':'Source evidence unavailable.',
            'next_step':'Original source content is unavailable or expired.'}

    human_qualified = signal.get('status') == 'Qualified'
    ai_buying_intent = signal.get('buying_intent')
    ai_confirmed = ai_buying_intent == 'Explicit commercial intent'

    is_market_intel = provenance.get('content_kind') in ('release','paper') or signal.get('category')=='Market / technology intelligence'
    if is_market_intel and not human_qualified:
        reasons.append('Technical releases and research papers are market/technology intelligence, not buyer opportunities.')

    has_negative = bool(NEGATIVE.search(source) or evidence.get('penalties') or ranking.get('excluded') or ranking.get('scoring',{}).get('dimensions',{}).get('contradictory_evidence',0)<0)
    if has_negative and not human_qualified:
        reasons.append('Negative or noncommercial evidence requires review before promotion.')

    for match in REQUEST.finditer(source):
        if OBJECT.search(match.group()) or re.search(r'\b(?:evaluating|comparing|buy|purchase|hire|alternative|replace|migrating|recommend)\b',match.group(),re.I):
            quote=match.group().strip();break

    if human_qualified:
        return {'policy_version':VERSION,'eligible':True,'intent_quote':quote or evidence.get('intent_phrase'),'reasons':[],
            'basis':'Human-qualified signal approved for Opportunity promotion.',
            'next_step':'Create Opportunity and assign priority and next action.'}

    if ai_confirmed and not reasons:
        return {'policy_version':VERSION,'eligible':True,'intent_quote':quote or evidence.get('intent_phrase'),'reasons':[],
            'basis':'AI-assessed explicit commercial intent with verified source quotes.',
            'next_step':'Review the AI-cited evidence and promote to an Opportunity.'}

    if not quote:
        reasons.append('No explicit request, evaluation, replacement or purchase consideration is evidenced yet. Qualify this signal or run AI Analysis first.')
    aligned=bool(evidence.get('matched_keywords') or evidence.get('matched_topics') or ranking.get('scoring',{}).get('dimensions',{}).get('problem_service_fit',0))
    if not aligned:
        reasons.append('No alignment to requested topics or reviewed service/ICP context is recorded.')
    return {'policy_version':VERSION,'eligible':not reasons,'intent_quote':quote,'reasons':reasons,
        'basis':'Observed request plus recorded targeting alignment; not a verified buyer, contact, budget or purchasing event.',
        'next_step':'Review the original request and unknowns.' if not reasons else 'Qualify this signal after reviewing evidence, or keep it saved for research.'}
