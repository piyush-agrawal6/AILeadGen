import {notFound} from 'next/navigation';
import {CompanyProfileSettings} from '@/components/workspaces/company-profile';
export default function CompanyPage(){
 if(process.env.HEYSOW_WORKSPACE_MANAGEMENT_ENABLED!=='true')notFound();
 return <CompanyProfileSettings/>;
}
