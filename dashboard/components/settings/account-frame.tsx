"use client";
import {useWorkspaceCapabilities} from '@/components/workspaces/features';
export function AccountSettingsFrame({children,navigation}:{children:React.ReactNode;navigation:React.ReactNode}){const c=useWorkspaceCapabilities();return <div className={c.leadEngineAvailable===false?'settings-layout-unified':'settings-layout'}>{c.leadEngineAvailable!==false&&navigation}<div className="settings-content">{children}</div></div>}
