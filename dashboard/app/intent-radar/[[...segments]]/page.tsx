import {notFound} from 'next/navigation';
import {IntentRadarExperience} from '@/components/intent-radar/experience';
const routes=['','discover','monitors','monitors/new','signals','opportunities','saved','alerts','integrations','settings','growth','growth/themes','growth/trends','growth/research','growth/saved','growth/watchlists','growth/reports','growth/competitors'];
export default async function Page({params}:{params:Promise<{segments?:string[]}>}){
 const {segments=[]}=await params,route=segments.join('/');
  if(!routes.includes(route)&&!/^\/(?:monitors|signals|opportunities|growth\/themes|growth\/research)\/[a-f0-9-]{36}$/.test('/'+route))notFound();
  return <IntentRadarExperience route={route}/>;
}
