"use client";
import {useQuery} from '@tanstack/react-query';
import {request} from '@/lib/intelligence';
import {Page,Table,Metrics} from '@/components/operations/ui';
type Row={template_id?:string;source?:string;sent:number;delivered:number;hard_bounced:number;replied:number;positive_reply:number;negative_reply:number;unsubscribe:number;meeting:number;positive_reply_rate:number|null};
type Results={ready:boolean;contacted_recipients:number;pdf_version:string;templates:Row[];sources:Row[];delivery_note:string};
export default function OutreachResults(){
 const q=useQuery({queryKey:['fixed-intro-results'],queryFn:()=>request<Results>('/email/intro-analytics'),refetchInterval:30000});
 const d=q.data;
 return <Page title="Outreach Results" description="Five fixed introductions · one PlaneByte company PDF · new contactable businesses only">
  {q.error&&<p role="alert">{q.error.message}</p>}
  {!d?<p role="status">Loading results…</p>:!d.ready?<p>The simplified outreach release is being configured.</p>:<>
   <Metrics items={[["Permanent contacted recipients",d.contacted_recipients],["Qualification","Contactable only"],["AI copy generation","Not used"],["PDF version",d.pdf_version]]}/>
   <p className="text-sm text-muted-foreground">Real business + valid public email + never contacted + safe to contact. Automatic website, SEO, security and Lighthouse analysis are disabled.</p>
   <a className="control inline-flex my-4" href={'/api/email/company-pdf/'+d.pdf_version} target="_blank" rel="noreferrer">View PlaneByte Capabilities &amp; Services PDF</a>
   {([['Template results',d.templates],['Acquisition sources',d.sources]] as const).map(([title,rows])=><section className="ops-panel" key={title}><h2>{title}</h2><div className="overflow-x-auto"><Table head={['Template / Source','Sent','Delivered','Hard bounce','Replies','Positive','Negative','Opt-outs','Meetings','Positive reply rate']}>{rows.map(r=><tr key={r.template_id||r.source}><td>{r.template_id||r.source}</td><td>{r.sent}</td><td>{r.delivered}</td><td>{r.hard_bounced}</td><td>{r.replied}</td><td>{r.positive_reply}</td><td>{r.negative_reply}</td><td>{r.unsubscribe}</td><td>{r.meeting}</td><td>{r.positive_reply_rate===null?'—':r.positive_reply_rate+'%'}</td></tr>)}</Table></div></section>)}
   <p className="text-xs text-muted-foreground">{d.delivery_note} Positive reply rate is the primary experiment metric.</p>
  </>}
 </Page>;
}
