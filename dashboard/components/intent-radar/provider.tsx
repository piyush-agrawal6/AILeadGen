"use client";
import {createContext,useCallback,useContext,type ReactNode} from 'react';
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query';
import {toast} from 'sonner';
import {request} from '@/lib/intelligence';
import {resolveRadarToast} from '@/lib/action-toast';
import {useWorkspace} from '@/components/workspaces/use-workspace';
import type {IntentCapabilities} from '@/lib/intent-radar';
const Context=createContext('');
const Endpoint=createContext('');
export function useMcpEndpoint(){return useContext(Endpoint)}
export function IntentRadarProvider({children,initialOrganization,mcpEndpoint=''}:{children:ReactNode;initialOrganization:string;mcpEndpoint?:string}){const workspace=useWorkspace();const org=workspace.data?workspace.data.active_organization_id||'':initialOrganization;return <Context.Provider value={org}><Endpoint.Provider value={mcpEndpoint}>{children}</Endpoint.Provider></Context.Provider>}
export function useRadarRead<T>(path:string,enabled=true,poll=false){const org=useContext(Context);return useQuery({queryKey:['intent-radar',org,path],queryFn:({signal})=>request<T>('/intent-radar'+path,{signal}),enabled:enabled&&!!org,retry:false,staleTime:10000,refetchInterval:query=>poll&&['QUEUED','RUNNING'].includes((query.state.data as {status?:string}|undefined)?.status||'')?10000:false})}
export function useRadarMutation(){
 const org=useContext(Context),client=useQueryClient();
 return useMutation({mutationFn:({path,method='POST',body}:{path:string;method?:string;body?:unknown})=>request<unknown>('/intent-radar'+path,{method,body:body===undefined?undefined:JSON.stringify(body)}),onSuccess:async(data,variables)=>{await Promise.all([client.invalidateQueries({queryKey:['intent-radar',org]}),client.invalidateQueries({queryKey:['workspace-notifications']})]);toast.success(resolveRadarToast(variables.path,variables.method,data));},onError:(error)=>toast.error(error.message)});
}
export function useRadarCapabilities(){return useRadarRead<IntentCapabilities>('/capabilities')}
export function useRadarRefresh(){const org=useContext(Context),client=useQueryClient();return useCallback(()=>{void client.invalidateQueries({queryKey:['intent-radar',org]});void client.invalidateQueries({queryKey:['workspace-notifications']})},[org,client])}
