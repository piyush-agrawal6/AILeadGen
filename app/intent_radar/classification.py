"""Transparent heuristics; never infer identity, budget or purchase authority."""
import re
from datetime import datetime, timezone

RULES = (
 ('Alternative search', r'\balternative(?:s)?\b|instead of|replace our'),
 ('Product comparison', r'\bvs\b|versus|compar(?:e|ing|ison)'),
 ('Recommendation request', r'recommend|looking for|any suggestions|what.*(?:tool|service).*(?:use|best)'),
 ('Problem / pain point', r'struggl|pain point|problem|frustrat|too (?:expensive|complex|slow)'),
 ('Purchase consideration', r'\bbuy(?:ing)?\b|\bpurchas|\bhir(?:e|ing)\b'),
 ('Tool / service evaluation', r'evaluat|considering|which.*(?:tool|service)'),
)

def classify(item, query):
    value = (item['title'] + ' ' + item['excerpt']).casefold()
    if any(term.casefold() in value for term in query.excluded): return None
    matched = list(dict.fromkeys(term for term in query.keywords if term.casefold() in value))
    # Retrieval remains a bounded public-source window. An English regex must
    # not decide whether a paraphrase or another language reaches the evaluator.
    semantic_candidate=bool(query.semantic and query.offerings)
    if not matched and not semantic_candidate: return None
    day = item['observed_at'][:10]
    if query.from_date and day < query.from_date.isoformat() or query.to_date and day > query.to_date.isoformat(): return None
    category, phrase = 'General discussion', None
    for label, pattern in RULES:
        hit = re.search(pattern, value)
        if hit: category, phrase = label, hit.group(0); break
    # A matching phrase is not proof that the author is seeking a vendor.
    # Preserve topical discussions while reducing obvious noncommercial contexts.
    noncommercial = [label for label,pattern in (
        ('Self-promotion', r'\bshow hn:|\blaunching\b|my new product|check out my'),
        ('Job advertisement', r'\b(?:is|are|we are) hiring\b|\bjob opening\b'),
        ('Explicitly non-buying', r'\bnot (?:looking to )?(?:buy|purchase|hire)\b|\bno (?:purchase|buying) plans\b'),
        ('Security announcement', r'\b(?:security|data) breach\b|\bsecurity advisory\b'),
    ) if re.search(pattern,value)]
    request = bool(re.search(r'looking for|seeking|can (?:anyone|someone)|any (?:recommendations|suggestions)|\b(?:we|i) (?:need|want|are comparing|am comparing)|what.*(?:tool|service).*(?:use|best)|which.*(?:tool|service)|\bhire\b|\bbuy(?:ing)?\b|\bpurchas', value))
    if noncommercial or category in ('Alternative search','Product comparison','Recommendation request') and not request:
        category,phrase='General discussion',None
    if query.categories and category not in query.categories: return None
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(item['observed_at'])).total_seconds()
    topics = [term for term in [*query.topics, *query.phrases] if term.casefold() in value]
    score = min(100, (20 if not matched else 40) + min(20, 10 * len(matched)) + (20 if phrase else 0) + min(10, 5 * len(topics)) + (5 if 0 <= age < 7 * 86400 else 0) + (5 if item['excerpt'] else 0))
    penalties=list(dict.fromkeys([*noncommercial,*[label for label,pattern in [('Homework/tutorial',r'homework|tutorial|assignment')] if re.search(pattern,value)]]))
    score=max(0,score-15*len(penalties))
    if not phrase:score=min(60,score)
    if not query.semantic and score < query.min_relevance: return None
    confidence = 'Strong evidence' if phrase and score >= 85 else 'Moderate evidence' if phrase else 'Needs review'
    return {**item, 'category': category, 'score': score, 'evidence': {'matched_keywords': matched, 'matched_topics': topics, 'intent_phrase': phrase,
             'confidence': confidence, 'method': 'DETERMINISTIC_V3', 'explanation': (f"Matched {', '.join(matched)}" + (f" and the phrase ‘{phrase}’." if phrase else '; no explicit intent phrase was found.') if matched else 'No exact keyword match. Observable request retained for human-requested semantic analysis; relevance is not yet verified.')+(f" Penalties: {', '.join(penalties)} (-15 each)." if penalties else ''),
             'observed_text': item['excerpt'] or item['title'], 'unknown': ['Identity', 'Budget', 'Purchase authority', 'Buying timeline', 'Geography', 'Language'],
              'semantic_candidate':semantic_candidate and not matched,'penalties':penalties,'scoring_version':'DETERMINISTIC_V3','purchasing_event_verified': False}}
