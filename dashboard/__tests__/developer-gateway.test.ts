import {it,expect,vi,beforeEach,afterEach} from 'vitest';
import {NextRequest} from 'next/server';
import {isDeveloperApiPath} from '@/lib/developer-path';
import {POST,GET} from '@/app/api/[...path]/route';
import {currentUser} from '@/lib/server/session';
vi.mock('server-only',()=>({}));
vi.mock('@/lib/server/private-session',()=>({privateSession:vi.fn(async()=>"private-backend-session-fixture")}));
vi.mock('@/lib/server/env',()=>({serverEnv:()=>({production:false,apiUrl:'http://backend.test',secret:'fixture-internal-signing-secret-only'})}));
vi.mock('@/lib/server/session',()=>({currentUser:vi.fn()}));
const token='pbk_00000000-0000-4000-8000-000000000001.'+'a'.repeat(43);
it.each([['TimeoutError',504],['NetworkError',502]] as const)('redacts destination failures: %s',async(name,status)=>{
 const log=vi.spyOn(console,'error').mockImplementation(()=>{});
 try{vi.mocked(fetch).mockRejectedValue(Object.assign(new Error('private-receiver-value'),{name}));const res=await GET(new NextRequest('http://localhost:3000/api/v1/signals?search=private-term-value',{headers:{Authorization:'Bearer '+token}}),{params:Promise.resolve({path:['v1','signals']})});expect(res.status).toBe(status);const output=JSON.stringify(log.mock.calls);expect(output).toContain(res.headers.get('x-request-id'));for(const privateValue of ['private-receiver-value','private-term-value',token])expect(output).not.toContain(privateValue);
 }finally{log.mockRestore();}
});
beforeEach(()=>{vi.stubEnv('HEYSOW_DEVELOPER_API_ENABLED','true');vi.mocked(currentUser).mockResolvedValue(null);vi.stubGlobal('fetch',vi.fn(async()=>Response.json({items:[]},{headers:{'retry-after':'30'}})))});
afterEach(()=>{vi.unstubAllGlobals();vi.unstubAllEnvs();vi.clearAllMocks()});
it('forwards only the exact versioned bearer route without fabricating a browser identity',async()=>{const r=new NextRequest('http://localhost:3000/api/v1/lists',{method:'POST',headers:{authorization:'Bearer '+token,'Idempotency-Key':'00000000-0000-4000-8000-000000000099','x-le-user':'forged@example.test'},body:JSON.stringify({name:'Controlled list'})});const response=await POST(r,{params:Promise.resolve({path:['v1','lists']})});expect(response.status).toBe(200);expect(currentUser).not.toHaveBeenCalled();const options=vi.mocked(fetch).mock.calls[0][1];expect(options?.headers).toMatchObject({authorization:'Bearer '+token,'idempotency-key':'00000000-0000-4000-8000-000000000099'});expect(Object.keys(options?.headers||{}).some(key=>key.startsWith('x-le-'))).toBe(false);expect(response.headers.get('retry-after')).toBe('30')});
it('requires the normal browser session on every existing internal route',async()=>{const response=await GET(new NextRequest('http://localhost:3000/api/leads',{headers:{authorization:'Bearer '+token}}),{params:Promise.resolve({path:['leads']})});expect(response.status).toBe(401);expect(fetch).not.toHaveBeenCalled()});
it('rejects malformed bearer credentials and keeps prefix lookalikes private',async()=>{const response=await GET(new NextRequest('http://localhost:3000/api/v1/companies',{headers:{authorization:'Bearer invalid'}}),{params:Promise.resolve({path:['v1','companies']})});expect(response.status).toBe(401);expect(fetch).not.toHaveBeenCalled();expect(isDeveloperApiPath('/api/v1/companies')).toBe(true);for(const path of ['/api/v1','/api/v10/companies','/api/v1evil/companies','/api/organization/developer/keys'])expect(isDeveloperApiPath(path)).toBe(false)});

it('keeps signed admission and private account endpoints off the general browser gateway',async()=>{
 vi.mocked(currentUser).mockResolvedValue({email:'person@example.test',name:'Person'});
 for(const segment of ['accounts','admission']){
  const response=await POST(new NextRequest('http://localhost:3000/api/organization/'+segment+'/google',{method:'POST',headers:{origin:'http://localhost:3000',host:'localhost:3000'},body:'{}'}),{params:Promise.resolve({path:['organization',segment,'google']})});
  expect(response.status).toBe(404);
 }
 expect(fetch).not.toHaveBeenCalled();
});
it('signs the private backend session and discards browser-supplied session headers',async()=>{
 vi.mocked(currentUser).mockResolvedValue({email:'person@example.test',name:'Person'});
 const response=await GET(new NextRequest('http://localhost:3000/api/organization/products',{headers:{'x-le-session':'forged-by-browser'}}),{params:Promise.resolve({path:['organization','products']})});
 expect(response.status).toBe(200);
 expect(vi.mocked(fetch).mock.calls[0][1]?.headers).toMatchObject({'x-le-session':'private-backend-session-fixture'});
});
