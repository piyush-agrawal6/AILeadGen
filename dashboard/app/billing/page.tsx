import {BillingWorkspace} from '@/components/workspaces/billing';
import {approvedPlan} from '@/lib/plan-intent';
import {selectedPlan} from '@/lib/server/plan-intent';
export const metadata={title:'Billing | Intent Radar by PlaneByte',robots:{index:false,follow:false}};
export default async function Billing({searchParams}:{searchParams:Promise<{plan?:string}>}){const p=await searchParams;return <BillingWorkspace selectedPlan={approvedPlan(p.plan)||await selectedPlan()}/>;}
