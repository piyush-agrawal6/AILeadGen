import {notFound} from 'next/navigation';
import {AccountProfileSettings} from '@/components/workspaces/account-profile';
export default function Profile(){if(process.env.HEYSOW_WORKSPACE_MANAGEMENT_ENABLED!=='true')notFound();return <AccountProfileSettings/>}
