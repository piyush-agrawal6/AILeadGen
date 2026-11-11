import Link from 'next/link';
import {productAccess} from '@/lib/server/products';
import {IntentRadarProvider} from '@/components/intent-radar/provider';
import './experience.css';
export const metadata={title:'Intent Radar | PlaneByte',robots:{index:false,follow:false}};
export default async function Layout({children}:{children:React.ReactNode}){
 const access=await productAccess();
 if(!access?.intent_radar.enabled)return <section className="settings-page"><header><h1>Intent Radar is unavailable</h1><p>This workspace does not have active Intent Radar access, or its access could not be verified.</p></header><Link className="control" href="/">Return to Lead Engine</Link></section>;
 return <IntentRadarProvider initialOrganization={access.organization_id!}><div className="ir">{children}</div></IntentRadarProvider>;
}
