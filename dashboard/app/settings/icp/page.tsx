import {notFound} from 'next/navigation';
import {ICPSettings} from '@/components/workspaces/icp-builder';
export default function ICP(){if(process.env.HEYSOW_WORKSPACE_MANAGEMENT_ENABLED!=='true')notFound();return <ICPSettings/>}
