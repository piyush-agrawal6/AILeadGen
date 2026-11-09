import {AcquisitionProgress} from '@/components/acquisition/progress';
export default async function Page({params}:{params:Promise<{id:string}>}){const {id}=await params;return <AcquisitionProgress id={id}/>}
