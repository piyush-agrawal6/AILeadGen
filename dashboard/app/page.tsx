import {redirect} from 'next/navigation';
import {productAccess} from '@/lib/server/products';
import {selectedPlan} from '@/lib/server/plan-intent';
import {leadEngineEnabled} from '@/lib/product-availability';
export default async function Home(){const plan=await selectedPlan();if(plan)redirect('/billing?plan='+plan);if(!leadEngineEnabled(process.env.LEAD_ENGINE_AVAILABLE))redirect('/intent-radar');const access=await productAccess();if(access?.intent_radar.enabled)redirect('/intent-radar');if(access?.lead_engine)redirect('/lead-engine');redirect('/settings');}
