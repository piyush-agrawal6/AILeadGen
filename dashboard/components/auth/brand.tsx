import Image from 'next/image';
import {brand} from '@/lib/brand';
export function PlaneByteBrand({compact=false}:{compact?:boolean}){return <span className="heysow-wordmark"><Image src={brand.mark} width={36} height={36} alt="" priority/>{!compact&&<span>{brand.name}</span>}</span>;}
