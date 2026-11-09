"use client";
import Link from 'next/link';
import {useQuery} from '@tanstack/react-query';
import {request} from '@/lib/intelligence';
import {Metrics} from './ui';
export function DataQuality(){const q=useQuery({queryKey:['data-quality'],queryFn:()=>request<Record<string,number>>('/foundation/quality')});return <section className="ops-panel"><div className="flex items-center justify-between gap-3 mb-4"><h2>Data Quality</h2><Link className="ops-link text-xs" href="/leads/review">Needs Review →</Link></div><Metrics items={[["Master Leads",q.data?.master_leads],["Usable published email",q.data?.with_usable_email],["With phone",q.data?.with_phone],["Social profile",q.data?.with_social],["Decision maker",q.data?.with_decision_maker],["Needs review",q.data?.needs_review],["Possible duplicates",q.data?.possible_duplicates],["Invalid addresses",q.data?.invalid_addresses],["Suppressed",q.data?.suppressed],["Missing website",q.data?.missing_website]]}/><p className="text-xs text-muted-foreground">Usable email counts require public-source evidence and mail-domain validation. These are operational data metrics.</p>{q.error&&<p role="alert">{q.error.message}</p>}</section>}
