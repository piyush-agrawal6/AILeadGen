'use client';
import {useTransition} from 'react';
import {useRouter} from 'next/navigation';
import Link from 'next/link';
export function WorkspaceAccessRetry(){const router=useRouter(),[pending,start]=useTransition();return <section className="settings-page"><header><h1>Workspace access could not be checked</h1><p>The access check did not complete. Retry to verify your current workspace permissions.</p></header><button className="control" disabled={pending} onClick={()=>start(()=>router.refresh())}>{pending?'Checking workspace access…':'Retry access check'}</button><Link className="control" href="/settings">Review workspace selection</Link></section>}
