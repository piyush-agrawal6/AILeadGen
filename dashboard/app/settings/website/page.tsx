import {notFound} from 'next/navigation';
import {WebsiteReview} from '@/components/workspaces/website-review';
export default function Website(){if(process.env.HEYSOW_WORKSPACE_MANAGEMENT_ENABLED!=='true'||process.env.HEYSOW_COMPANY_DISCOVERY_ENABLED!=='true')notFound();return <WebsiteReview/>}
