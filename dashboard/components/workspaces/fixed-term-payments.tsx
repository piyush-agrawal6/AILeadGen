'use client';
import {useState} from 'react';
import {useQueryClient} from '@tanstack/react-query';
import {request} from '@/lib/intelligence';
import {Button} from '@/components/ui/button';
type Order={id:string;provider:string;mode:string;plan_code:string;interval:string;currency:string;total_minor:number;tax_minor:number;status:string;period_start:number|null;period_end:number|null;created_at:string};
export type FixedTermData={mode?:'test'|'live';items:Order[];refunds?:{order_id:string;amount_minor:number;currency:string|null;status:string}[];refund_requests?:{id:string;order_id:string;status:string}[];checkout_enabled:boolean;yearly_prices_approved:boolean;renewal:string;upgrade_policy:string};
const money=(minor:number,currency='USD')=>new Intl.NumberFormat('en-US',{style:'currency',currency}).format(minor/100);
export function FixedTermPayments({data}:{data:FixedTermData;plans:{code:string;name:string;monthly_minor:number|null}[]}){
 const query=useQueryClient(),[busy,setBusy]=useState(false),[message,setMessage]=useState<string|null>(null);
 async function refund(id:string){setBusy(true);try{await request('/organization/billing/access/orders/'+id+'/refund-request',{method:'POST',body:JSON.stringify({request_id:crypto.randomUUID()})});await query.invalidateQueries({queryKey:['workspace-usage']});setMessage('Refund request recorded for review. No money has been refunded yet.');}catch{setMessage('The review request could not be saved. Contact support with your order reference.');}finally{setBusy(false)}}
 if(!data.items.length)return null;
 return <section className="space-y-4 rounded-xl border bg-card p-5"><h3 className="font-semibold">Historical prepaid purchases</h3><p className="text-sm text-muted-foreground">Original access dates, receipts and refund-review rights are preserved. These purchases do not renew automatically. All new subscriptions use Creem above.</p><div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr>{['Date','Plan','Amount','Status','Records'].map(v=><th className="p-2" key={v}>{v}</th>)}</tr></thead><tbody>{data.items.map(item=><tr className="border-t" key={item.id}><td className="p-2">{new Date(item.created_at).toLocaleDateString()}</td><td className="p-2">{item.plan_code}</td><td className="p-2">{money(item.total_minor,item.currency)}</td><td className="p-2">{item.status}</td><td className="p-2"><a className="underline" href={'/api/organization/billing/access/orders/'+item.id+'/receipt'}>Receipt</a>{item.status==='PAID'&&<Button variant="outline" size="sm" disabled={busy} onClick={()=>void refund(item.id)}>Request refund review</Button>}</td></tr>)}</tbody></table></div>{message&&<p role="status" className="text-sm">{message}</p>}</section>;
}
