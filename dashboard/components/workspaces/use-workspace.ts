"use client";
import {useQuery} from '@tanstack/react-query';
import {request} from '@/lib/intelligence';
export type Membership={organization_id:string;name:string;role:'OWNER'|'ADMIN'|'MEMBER'|'VIEWER'};
export type WorkspaceSummary={items:Membership[];active_organization_id:string|null;active_onboarding_status:string|null;active_is_internal?:boolean};
export function useWorkspace(enabled=true){
 const query=useQuery({queryKey:['account-workspaces'],queryFn:()=>request<WorkspaceSummary>('/organization/workspaces'),enabled,retry:false});
 const active=query.data?.items.find(item=>item.organization_id===query.data?.active_organization_id);
 return {...query,active,canManage:active?.role==='OWNER'||active?.role==='ADMIN',isInternal:query.data?.active_is_internal===true};
}
export function initials(name:string){return name.trim().split(/\s+/).filter(Boolean).slice(0,2).map(word=>word.replace(/[^\p{L}\p{N}]/gu,'').slice(0,1)).join('').toUpperCase()||'W'}
