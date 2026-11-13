import {redirect} from 'next/navigation';
import {productAccess} from '@/lib/server/products';
import {selectedPlan} from '@/lib/server/plan-intent';
export default async function Home(){const plan=await selectedPlan();if(plan)redirect('/billing?plan='+plan);const access=await productAccess();if(access?.intent_radar.enabled)redirect('/intent-radar');if(access?.lead_engine)redirect('/lead-engine');redirect('/settings');}
