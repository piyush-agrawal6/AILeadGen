import {notFound} from 'next/navigation';
import {DomainSettings} from '@/components/workspaces/domains';
export default function Domains(){if(process.env.HEYSOW_WORKSPACE_MANAGEMENT_ENABLED!=='true')notFound();return <DomainSettings/>}
