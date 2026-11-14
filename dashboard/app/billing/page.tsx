import {UsageOverview} from '@/components/workspaces/usage';
import {approvedPlan} from '@/lib/plan-intent';
import {selectedPlan} from '@/lib/server/plan-intent';
export const metadata={title:'Billing & usage | PlaneByte'};
export default async function Page({searchParams}:{searchParams:Promise<{plan?:string}>}){const p=await searchParams;return <UsageOverview selectedPlan={approvedPlan(p.plan)||await selectedPlan()}/>}
