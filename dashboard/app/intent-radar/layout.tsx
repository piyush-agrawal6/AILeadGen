import {WorkspaceAccessRetry} from '@/components/intent-radar/access-retry';
import {WorkspaceAccessScreen} from '@/components/intent-radar/workspace-access-screen';
import {productAccess} from '@/lib/server/products';
import {IntentRadarProvider} from '@/components/intent-radar/provider';
import {serverEnv} from '@/lib/server/env';
import {publicMcpEndpoint} from '@/lib/mcp-configuration';
import './experience.css';
export const metadata={title:'Intent Radar | PlaneByte',robots:{index:false,follow:false}};
export default async function Layout({children}:{children:React.ReactNode}){
 const access=await productAccess();
 if(!access)return <WorkspaceAccessRetry/>;
 if(!access.intent_radar.enabled)return <WorkspaceAccessScreen access={access}/>;
 return <IntentRadarProvider initialOrganization={access.organization_id!} mcpEndpoint={publicMcpEndpoint(serverEnv().apiUrl)}><div className="ir">{children}</div></IntentRadarProvider>;
}
