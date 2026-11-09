"use client";
import {useState} from 'react';
import {useQueryClient} from '@tanstack/react-query';
import {CampaignSelect} from '@/components/operations/ui';
import {ImportLeads} from '@/components/acquisition/import-leads';

export function EmailAudienceSource({value,onChange}:{value:string|null;onChange:(id:string|null)=>void}){
 const [source,setSource]=useState<'campaign'|'upload'>('campaign');
 const [uploaded,setUploaded]=useState<string|null>(null);const client=useQueryClient();
 function select(next:'campaign'|'upload'){setSource(next);if(next==='upload'&&!uploaded)onChange(null)}
 function imported(id:string){setUploaded(id);onChange(id);void client.invalidateQueries()}
 return <section className="space-y-4 rounded-lg border p-4"><fieldset><legend className="mb-3 text-sm font-medium">Email audience source</legend><div className="flex flex-wrap gap-4"><label className="flex gap-2 text-sm"><input type="radio" name="email-audience-source" checked={source==='campaign'} onChange={()=>select('campaign')}/>Select campaign</label><label className="flex gap-2 text-sm"><input type="radio" name="email-audience-source" checked={source==='upload'} onChange={()=>select('upload')}/>Upload CSV / Excel</label></div></fieldset>{source==='campaign'||uploaded?<><CampaignSelect value={value} onChange={onChange}/>{uploaded&&source==='upload'&&<p role="status" className="text-xs">Uploaded leads are linked to the selected campaign. Review eligibility, messages and PDFs before starting emails.</p>}</>:<ImportLeads inline onImported={imported}/>}</section>
}
