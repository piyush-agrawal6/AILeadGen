"use client";
import {createContext,useContext} from 'react';
export const WorkspaceFeatures=createContext(false);
export function useWorkspaceManagement(){return useContext(WorkspaceFeatures)}
export type WorkspaceCapabilities={companyDiscovery:boolean;customerIntegrations?:boolean;leadAssistant?:boolean;developerApi?:boolean};
export const CapabilityFeatures=createContext<WorkspaceCapabilities>({companyDiscovery:false});
export function useWorkspaceCapabilities(){return useContext(CapabilityFeatures)}
