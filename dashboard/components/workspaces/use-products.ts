"use client";
import {useQuery} from '@tanstack/react-query';
import {request} from '@/lib/intelligence';
import {useWorkspace} from './use-workspace';
import {useWorkspaceManagement} from './features';
import type {ProductAccess} from '@/lib/intent-radar';
export function useProducts(){
 const management=useWorkspaceManagement(),workspace=useWorkspace(management);
  return useQuery({queryKey:['plane-products',workspace.data?.active_organization_id],queryFn:({signal})=>request<ProductAccess>('/organization/products',{signal}),enabled:management&&!!workspace.data?.active_organization_id,retry:false,staleTime:0,refetchOnWindowFocus:'always'});
}
