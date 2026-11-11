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
export function IntentRadarExperience({route}:{route:string}){
 const access=useRadarCapabilities();
 if(access.error)return <ErrorState message={access.error.message} retry={()=>void access.refetch()}/>;
 if(!access.data)return <LoadingSkeleton/>;
 if(route.startsWith('monitors'))return <MonitorsExperience route={route}/>;
  if(route.startsWith('signals/'))return <EvidenceDetail id={route.split('/')[1]}/>;
  if(route.startsWith('opportunities/'))return <OpportunitiesWorkspace id={route.split('/')[1]}/>;
 switch(route){case 'discover':return <DiscoverExperience/>;case 'signals':return <SignalsWorkspace/>;case 'opportunities':return <OpportunitiesWorkspace/>;case 'saved':return <SavedResearch/>;case 'alerts':return <AlertsInbox/>;case 'settings':return <RadarSettings/>;case 'integrations':return <IntegrationsPage/>;default:return <OverviewDashboard/>}
}
