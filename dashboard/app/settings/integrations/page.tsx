import {notFound} from 'next/navigation';
import {IntegrationSettings} from '@/components/workspaces/integrations';
import {GmailSettings} from '@/components/workspaces/gmail';
export default function Integrations(){if(process.env.HEYSOW_WORKSPACE_MANAGEMENT_ENABLED!=='true'||process.env.HEYSOW_CUSTOMER_INTEGRATIONS_ENABLED!=='true')notFound();return <div className="space-y-8"><IntegrationSettings/>{process.env.HEYSOW_CUSTOMER_GMAIL_ENABLED==='true'&&<GmailSettings/>}</div>}
