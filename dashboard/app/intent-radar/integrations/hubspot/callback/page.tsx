'use client';
import {useEffect,useRef,useState} from 'react';
import Link from 'next/link';
import {request} from '@/lib/intelligence';
export default function HubSpotCallback(){
  const started=useRef(false),[message,setMessage]=useState('Verifying HubSpot authorization…');
  useEffect(()=>{if(started.current)return;started.current=true;const u=new URL(location.href);history.replaceState(null,'',u.pathname);const code=u.searchParams.get('code'),state=u.searchParams.get('state');if(!code||!state||u.searchParams.has('error')){setMessage('Authorization did not complete.');return}
    void request('/intent-radar/hubspot/connect',{method:'POST',body:JSON.stringify({code,state})}).then(()=>setMessage('Portal identity and permissions verified.')).catch(()=>setMessage('Connection could not be verified. Restart from the same workspace.'));
  },[]);
  return <main><h1>HubSpot</h1><p role="status">{message}</p><Link href="/intent-radar/integrations/hubspot">Back to connection</Link></main>
}
