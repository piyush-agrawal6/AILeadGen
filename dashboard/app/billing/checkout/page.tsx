import {headers} from 'next/headers';
import {BillingCheckout} from '@/components/workspaces/billing-checkout';
export default async function Checkout({searchParams}:{searchParams:Promise<{subscription?:string}>}){const p=await searchParams;return <BillingCheckout id={p.subscription||''} nonce={(await headers()).get('x-nonce')||''}/>;}
