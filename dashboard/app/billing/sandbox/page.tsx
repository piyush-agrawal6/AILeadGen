import {BillingWorkspace} from '@/components/workspaces/billing';
import {approvedPlan} from '@/lib/plan-intent';
import {selectedPlan} from '@/lib/server/plan-intent';
export default async function Page({searchParams}:{searchParams:Promise<{plan?:string}>}){const p=await searchParams;return <BillingWorkspace selectedPlan={approvedPlan(p.plan)||await selectedPlan()}/>}
