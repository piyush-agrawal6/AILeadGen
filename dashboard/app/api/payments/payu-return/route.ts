import {NextRequest,NextResponse} from 'next/server';
import {serverEnv} from '@/lib/server/env';
export const runtime='nodejs';
export const maxDuration=30;
/** PayU return is untrusted until the API validates its hash and verifies it. */
export async function POST(request:NextRequest){
 if(!serverEnv().accounts)return NextResponse.json({detail:'Payment return is unavailable.'},{status:404});
 if(request.headers.get('content-type')?.split(';')[0]!=='application/x-www-form-urlencoded')return NextResponse.json({detail:'Invalid payment return.'},{status:415});
 const reader=request.body?.getReader(),chunks:Uint8Array[]=[];let size=0;
 if(reader)for(;;){const next=await reader.read();if(next.done)break;size+=next.value.length;if(size>16384){await reader.cancel();return NextResponse.json({detail:'Payment return exceeds its bound.'},{status:413});}chunks.push(next.value);}
 const body=Buffer.concat(chunks.map(chunk=>Buffer.from(chunk)));
 let status='pending';
 try{const result=await fetch(serverEnv().apiUrl+'/api/billing/payments/payu/callback',{method:'POST',headers:{'content-type':'application/x-www-form-urlencoded'},body,cache:'no-store',redirect:'error',signal:AbortSignal.timeout(25000)});if(result.ok){const data=await result.json();if(data.payment_verified===true)status='verified';else if(data.status==='FAILED')status='failed';}}catch{/* A return never invents success or retries a payment POST. */}
 // Fixed same-origin destination. Never reflect callback text, amount or URL.
 return NextResponse.redirect(new URL('/settings/billing?payment='+status,request.url),{status:303,headers:{'Cache-Control':'private, no-store'}});
}
