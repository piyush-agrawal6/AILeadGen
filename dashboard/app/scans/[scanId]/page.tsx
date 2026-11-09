import {redirect,notFound} from 'next/navigation';
export default async function HistoricalDiscovery({params}:{params:Promise<{scanId:string}>}){const {scanId}=await params;if(!/^\d+$/.test(scanId))notFound();redirect('/discovery/'+scanId)}
