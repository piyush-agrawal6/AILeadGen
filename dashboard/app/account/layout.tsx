import {AccountSettingsFrame} from '@/components/settings/account-frame';
import {notFound} from 'next/navigation';
import {SectionNavigation} from '@/components/settings/section-navigation';
export default function AccountLayout({children}:{children:React.ReactNode}){if(process.env.HEYSOW_WORKSPACE_MANAGEMENT_ENABLED!=='true')notFound();return <AccountSettingsFrame navigation={<SectionNavigation label="Account categories" sections={[{name:'Your account',links:[{href:'/account',title:'Account overview'},{href:'/account/profile',title:'Personal profile'},{href:'/account/appearance',title:'Appearance'},{href:'/account/security',title:'Sign-in & security'}]}]}/>}>{children}</AccountSettingsFrame>}
