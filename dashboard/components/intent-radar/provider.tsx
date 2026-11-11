"use client";
import {createContext,useCallback,useContext,type ReactNode} from 'react';
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query';
import {toast} from 'sonner';
import {request} from '@/lib/intelligence';
import {useWorkspace} from '@/components/workspaces/use-workspace';
import type {IntentCapabilities} from '@/lib/intent-radar';
const Context=createContext('');
export function IntentRadarProvider({children,initialOrganization}:{children:ReactNode;initialOrganization:string}){const workspace=useWorkspace();const org=workspace.data?workspace.data.active_organization_id||'':initialOrganization;return <Context.Provider value={org}>{children}</Context.Provider>}
export function useRadarRead<T>(path:string,enabled=true){const org=useContext(Context);return useQuery({queryKey:['intent-radar',org,path],queryFn:({signal})=>request<T>('/intent-radar'+path,{signal}),enabled:enabled&&!!org,retry:false})}
export function useRadarMutation(){
 const org=useContext(Context),client=useQueryClient();
 return useMutation({mutationFn:({path,method='POST',body}:{path:string;method?:string;body?:unknown})=>request<unknown>('/intent-radar'+path,{method,body:body===undefined?undefined:JSON.stringify(body)}),onSuccess:async()=>{await Promise.all([client.invalidateQueries({queryKey:['intent-radar',org]}),client.invalidateQueries({queryKey:['workspace-notifications']})]);toast.success('Intent Radar updated.');},onError:(error)=>toast.error(error.message)});
}
export function useRadarCapabilities(){return useRadarRead<IntentCapabilities>('/capabilities')}
export function useRadarRefresh(){const org=useContext(Context),client=useQueryClient();return useCallback(()=>{void client.invalidateQueries({queryKey:['intent-radar',org]});void client.invalidateQueries({queryKey:['workspace-notifications']})},[org,client])}
