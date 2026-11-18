"use client";
import {useRadarCapabilities} from './provider';
import {ErrorState,LoadingSkeleton} from './ui';
import {OverviewDashboard} from './overview';
import {DiscoverExperience} from './discovery';
import {MonitorsExperience} from './monitor-experience';
import {SignalsWorkspace} from './signal-workspace';
import {EvidenceDetail} from './evidence-experience';
import {OpportunitiesWorkspace,SavedResearch,AlertsInbox} from './research-experience';
import {RadarSettings} from './settings-experience';
import {IntegrationsPage} from './integrations';
import {IntelligenceGraph} from './intelligence-graph';
import {AssistantWorkspace} from './assistant-panel';
import {GrowthExperience} from './growth-experience';
import {UnifiedSettingsCenter} from '@/components/settings/unified-settings-center';
import {GitHubOAuthCallbackView} from './github-callback';
export function IntentRadarExperience({route}:{route:string}){
 const access=useRadarCapabilities();
 if(access.error)return <ErrorState message={access.error.message} retry={()=>void access.refetch()}/>;
 if(route==='integrations/github/callback')return <GitHubOAuthCallbackView/>;

 if(route==='growth'||route.startsWith('growth/'))return !access.data?<LoadingSkeleton/>:access.data.growth_enabled?<GrowthExperience route={route}/>:<ErrorState message="Growth Intelligence is not enabled for this workspace."/>;
 if(route.startsWith('monitors'))return <MonitorsExperience route={route}/>;
  if(route.startsWith('signals/'))return <EvidenceDetail id={route.split('/')[1]}/>;
  if(route.startsWith('opportunities/'))return <OpportunitiesWorkspace id={route.split('/')[1]}/>;
 if(route==='graph')return <IntelligenceGraph/>;
 if(route==='assistant')return !access.data?<LoadingSkeleton/>:access.data.growth_enabled?<AssistantWorkspace/>:<ErrorState message="AI Assistant is not enabled for this workspace."/>;
 switch(route){case 'discover':return <DiscoverExperience/>;case 'signals':return <SignalsWorkspace/>;case 'opportunities':return <OpportunitiesWorkspace/>;case 'saved':return <SavedResearch/>;case 'alerts':return <AlertsInbox/>;case 'settings':return <UnifiedSettingsCenter initialCategory="preferences" initialTab="discovery"/>;case 'integrations':return <UnifiedSettingsCenter initialCategory="integrations" initialTab="sources"/>;default:return <OverviewDashboard/>}
}
