import {notFound} from 'next/navigation';
import {InvitationSettings} from '@/components/workspaces/invitations';
export default function Team(){if(process.env.HEYSOW_WORKSPACE_MANAGEMENT_ENABLED!=='true')notFound();return <InvitationSettings/>}
