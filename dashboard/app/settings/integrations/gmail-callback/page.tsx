import {notFound} from 'next/navigation';
import {GmailCallback} from '@/components/workspaces/gmail';
export default function Callback(){if(process.env.HEYSOW_CUSTOMER_GMAIL_ENABLED!=='true'||process.env.HEYSOW_CUSTOMER_INTEGRATIONS_ENABLED!=='true'||process.env.HEYSOW_WORKSPACE_MANAGEMENT_ENABLED!=='true')notFound();return <GmailCallback/>}
