"use client";
import {useEffect,useRef,useState} from 'react';
import Link from 'next/link';
import {request} from '@/lib/intelligence';
export default function Callback(){
  const ran=useRef(false),[message,setMessage]=useState('Completing workspace authorization…');
  useEffect(()=>{if(ran.current)return;ran.current=true;const url=new URL(window.location.href);window.history.replaceState({},'',url.pathname);const code=url.searchParams.get('code'),state=url.searchParams.get('state');
    if(!code||!state||url.searchParams.has('error')){setMessage('Authorization was not completed.');return;}
    void request('/intent-radar/sheets/connect',{method:'POST',body:JSON.stringify({code,state})}).then(()=>setMessage('Authorization saved. Check a destination spreadsheet to verify access.')).catch(()=>setMessage('Authorization failed. Restart from the same workspace.'));
  },[]);
  return <section className="ops-page"><h1>Google Sheets</h1><p role="status">{message}</p><Link href="/intent-radar/integrations/sheets">Return to workspace connections</Link></section>;
}
