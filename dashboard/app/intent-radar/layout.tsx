import Link from 'next/link';
import {WorkspaceAccessRetry} from '@/components/intent-radar/access-retry';
import {productAccess} from '@/lib/server/products';
import {IntentRadarProvider} from '@/components/intent-radar/provider';
import {serverEnv} from '@/lib/server/env';
import {publicMcpEndpoint} from '@/lib/mcp-configuration';
import './experience.css';
export const metadata={title:'Intent Radar | PlaneByte',robots:{index:false,follow:false}};
export default async function Layout({children}:{children:React.ReactNode}){
 const access=await productAccess();
 if(!access)return <WorkspaceAccessRetry/>;
 if(!access.intent_radar.enabled)return <section className="settings-page"><header><h1>Intent Radar access is restricted</h1><p>This workspace does not have verified Intent Radar access. Review your selected workspace or contact its owner. No access has been granted automatically.</p></header><Link className="control" href="/settings">Review workspace access</Link></section>;
 return <IntentRadarProvider initialOrganization={access.organization_id!} mcpEndpoint={publicMcpEndpoint(serverEnv().apiUrl)}><div className="ir">{children}</div></IntentRadarProvider>;
}
