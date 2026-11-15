import type {OpportunityEligibility} from '@/lib/intent-radar';
export function OpportunityEvidence({policy}:{policy?:OpportunityEligibility}){
 if(!policy)return null;
 return <div className="ir-notice"><strong>{policy.eligible?'Evidence-backed review candidate':'Needs evidence review'}</strong>{policy.intent_quote&&<blockquote>{policy.intent_quote}</blockquote>}{policy.reasons.map(reason=><p key={reason}>{reason}</p>)}<small>{policy.basis} {policy.next_step}</small></div>;
}
