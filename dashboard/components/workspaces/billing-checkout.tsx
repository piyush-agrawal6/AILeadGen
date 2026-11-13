'use client';
import Link from 'next/link';
import Script from 'next/script';
import {useState} from 'react';
import {useQuery} from '@tanstack/react-query';
import {request} from '@/lib/intelligence';
import {Page} from '@/components/operations/ui';
import {useProducts} from '@/components/workspaces/use-products';
type Configuration={key:string;subscription_id:string;name:string;description:string;mode:'test';local_subscription_id:string};
type Receipt={razorpay_payment_id:string;razorpay_signature:string};
type Options=Configuration&{handler:(receipt:Receipt)=>void;modal:{ondismiss:()=>void};theme:{color:string}};
type RazorpayInstance={open:()=>void;on:(event:'payment.failed',callback:()=>void)=>void};
declare global{interface Window{Razorpay?:new(options:Options)=>RazorpayInstance}}
export function BillingCheckout({id,nonce}:{id:string;nonce:string}){
 const org=useProducts().data?.organization_id,[ready,setReady]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const valid=/^[a-f0-9-]{36}$/.test(id);
 const q=useQuery({queryKey:['billing-checkout',org,id],queryFn:()=>request<Configuration>('/organization/billing/subscriptions/'+id+'/checkout'),enabled:valid&&!!org,retry:false});
 function open(){if(!q.data||!window.Razorpay||q.data.mode!=='test'||!q.data.key.startsWith('rzp_test_'))return;setBusy(true);setError('');const checkout=new window.Razorpay({...q.data,theme:{color:'#4f46e5'},modal:{ondismiss:()=>{setBusy(false);setError('Checkout was closed. No payment or access is assumed. You can resume the same subscription.');}},handler:receipt=>{void request('/organization/billing/subscriptions/'+id+'/verify',{method:'POST',body:JSON.stringify({payment_id:receipt.razorpay_payment_id,signature:receipt.razorpay_signature})}).then(()=>window.location.assign('/billing/success?subscription='+id)).catch(e=>{setError(e.message);setBusy(false);});}});checkout.on('payment.failed',()=>{setError('The test payment failed. Your subscription has not been marked paid. Recheck its provider status before trying again.');setBusy(false);});checkout.open();}
 return <Page title="Authorize test subscription" description="Razorpay Test Mode · owner-controlled billing acceptance"><section className="ops-panel max-w-2xl"><h2>No real payment will be collected</h2><p>Only Razorpay’s documented sandbox payment details may be used. This recurring test mandate never grants a live paid subscription.</p>{q.isPending&&valid&&<p role="status">Loading the existing subscription…</p>}{(!valid||q.error)&&<p role="alert">{q.error?.message||'Choose a valid workspace subscription from billing.'}</p>}{q.data&&<><p className="my-4 font-semibold">{q.data.description}</p><Script src="https://checkout.razorpay.com/v1/checkout.js" nonce={nonce} strategy="afterInteractive" onReady={()=>setReady(true)} onError={()=>setError('Razorpay Checkout could not load. Retry the page; no new subscription is needed.')}/><button className="control ops-primary" disabled={!ready||busy} onClick={open}>{busy?'Awaiting test authorization…':ready?'Open Razorpay test checkout':'Loading secure checkout…'}</button></>}{error&&<p role="alert" className="mt-4">{error}</p>}<Link href="/billing" className="mt-5 block underline">Return to billing</Link></section></Page>;
}
