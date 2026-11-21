"use client";
import {useRadarCapabilities} from './provider';
import {ErrorState,LoadingSkeleton} from './ui';
import {OverviewDashboard} from './overview';
import {DiscoverExperience} from './discovery';
import {MonitorsExperience} from './monitor-experience';
import {SignalsWorkspace} from './signal-workspace';
import {EvidenceDetail} from './evidence-experience';
import {OpportunitiesWorkspace} from './opportunities/OpportunitiesWorkspace';
import {SavedResearch,AlertsInbox} from './research-experience';
import {ResearchLibraryWorkspace} from './saved/ResearchLibraryWorkspace';
import {RadarSettings} from './settings-experience';
import {CustomerIntegrationsCatalog} from './integrations/CustomerIntegrationsCatalog';
import {RadarSheets} from './integrations/RadarSheets';
import {ActionCenter} from './ActionCenter';
import {WebhookSettings} from '../workspaces/webhook-settings';
import {useWorkspace} from '../workspaces/use-workspace';
import {useRadarRead} from './provider';
function RadarHooks(){const org=useWorkspace().data?.active_organization_id;const status=useRadarRead<{webhooks:boolean}>('/destinations');return org&&status.data?.webhooks&&!status.isError?<WebhookSettings key={org} workspace={org} radar/>:<p role="status">Webhook management requires an entitled administrator and configured delivery service.</p>}
import {IntelligenceGraph} from './intelligence-graph';
import {AssistantPageClient} from '@/components/intelligence/AssistantPageClient';
import {GrowthExperience} from './growth-experience';
import {UnifiedSettingsCenter} from '@/components/settings/unified-settings-center';
import {GitHubOAuthCallbackView} from './github-callback';
import {IdealCustomersWorkspace} from './ideal-customers/IdealCustomersWorkspace';
export function IntentRadarExperience({route}:{route:string}){
 const access=useRadarCapabilities();
 // Static catalog routes — do not need backend radar capabilities
 if(route==='integrations')return <CustomerIntegrationsCatalog/>;
 if(route==='actions')return access.data?.actions_enabled?<ActionCenter/>:<p role="status">{access.isLoading?'Loading workspace…':'Action Center is unavailable for this workspace.'}</p>;
 if(route==='integrations/sheets')return <RadarSheets/>;
 if(route==='integrations/webhooks')return <RadarHooks/>;
 if(route==='integrations/github/callback')return <GitHubOAuthCallbackView/>;
 if(access.error)return <ErrorState message={access.error.message} retry={()=>void access.refetch()}/>;

 if(route==='ideal-customers'||route.startsWith('ideal-customers/'))return <IdealCustomersWorkspace route={route}/>;

 if(route==='growth'||route.startsWith('growth/'))return !access.data?<LoadingSkeleton/>:access.data.growth_enabled?<GrowthExperience route={route}/>:<ErrorState message="Growth Intelligence is not enabled for this workspace."/>;
 if(route==='discover'||route.startsWith('discover/'))return <DiscoverExperience route={route}/>;
 if(route.startsWith('monitors'))return <MonitorsExperience route={route}/>;
  if(route.startsWith('signals/'))return <EvidenceDetail id={route.split('/')[1]}/>;
  if(route.startsWith('opportunities/'))return <OpportunitiesWorkspace id={route.split('/')[1]}/>;
 if(route==='graph')return <OverviewDashboard/>;
 if(route==='assistant')return <AssistantPageClient/>;
 switch(route){case 'signals':return <SignalsWorkspace/>;case 'opportunities':return <OpportunitiesWorkspace/>;case 'saved':return <ResearchLibraryWorkspace/>;case 'alerts':return <AlertsInbox/>;case 'settings':return <UnifiedSettingsCenter initialCategory="preferences" initialTab="discovery"/>;case 'integrations':return <CustomerIntegrationsCatalog/>;default:return <OverviewDashboard/>}
}
