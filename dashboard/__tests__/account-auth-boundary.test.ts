import {beforeEach,describe,expect,it,vi} from 'vitest';
type TestToken={email?:string;planeByteSession?:string};
type TestUser=TestToken&{name?:string;planeByteAdmitted?:boolean};
type Config={callbacks:{jwt(input:{token:TestToken;user?:TestUser}):TestToken;session(input:{session:{user:TestUser};token:TestToken}):Promise<{user:TestUser}>;signIn(input:{user:TestUser;account:{provider:string}}):Promise<boolean>};providers:{id:string;options:{authorize(input:{email:string;password:string}):Promise<TestUser>}}[]};
const state=vi.hoisted(()=>({config:undefined as Config|undefined,request:vi.fn(),env:{accounts:true,customerAccess:true,production:false,allowed:[],secret:'fixture-cookie-key-at-least-thirty-two-characters',apiUrl:'http://backend.test',termsVersion:'fixture-terms'}}));
vi.mock('server-only',()=>({}));
vi.mock('next/headers',()=>({cookies:async()=>({get:()=>undefined}),headers:async()=>new Headers()}));
vi.mock('@/lib/server/env',()=>({serverEnv:()=>state.env}));
vi.mock('@/lib/server/account-broker',()=>({accountRequest:state.request}));
vi.mock('@/lib/server/admission',()=>({admitGoogle:vi.fn()}));
vi.mock('next-auth',()=>({default:(config:Config)=>{state.config=config;return {handlers:{},auth:vi.fn(),signIn:vi.fn(),signOut:vi.fn()}}}));
import '@/auth';
import {sealAccountCookie,openAccountCookie} from '@/lib/server/account-cookies';

describe('private account capability boundary',()=>{
 beforeEach(()=>state.request.mockReset());
 it('invalidates previously signed personal-email JWTs instead of exposing an authenticated session',()=>{
  expect(state.config!.callbacks.jwt({token:{email:'planebyte@gmail.com'}})).toBeNull();
 });
 it('keeps the opaque backend capability out of public Auth.js sessions',async()=>{
  const token=state.config!.callbacks.jwt({token:{email:'owner@example.com'},user:{email:'owner@example.com',planeByteAdmitted:true,planeByteSession:'PRIVATE-BACKEND-CAPABILITY'}});
  expect(token.planeByteSession).toBe('PRIVATE-BACKEND-CAPABILITY');
  const session=await state.config!.callbacks.session({session:{user:{email:'OWNER@example.com',name:'Owner'}},token});
  expect(session.user.email).toBe('owner@example.com');expect(session.user.planeByteAdmitted).toBe(true);
  expect(JSON.stringify(session)).not.toContain('PRIVATE-BACKEND-CAPABILITY');expect(session.user).not.toHaveProperty('planeByteSession');
 });
 it('rejects a successful credential response attributed to another identity',async()=>{
  const provider=state.config!.providers.find(p=>p.id==='credentials')!;
  state.request.mockResolvedValue({ok:true,data:{email:'someone-else@example.com',session_token:'private-token'}});
  expect(await provider.options.authorize({email:'owner@example.com',password:'A fixture passphrase 932!'})).toBeNull();
 });
 it('authenticates credential users only after the actual broker returns a private session',async()=>{
  const provider=state.config!.providers.find(p=>p.id==='credentials')!;
  state.request.mockResolvedValue({ok:true,data:{email:'owner@example.com',name:'Owner',session_token:'private-token'}});
  const user=await provider.options.authorize({email:'owner@example.com',password:'A fixture passphrase 932!'});
  expect(user.email).toBe('owner@example.com');expect(user.planeByteSession).toBe('private-token');
  expect(await state.config!.callbacks.signIn({user,account:{provider:'credentials'}})).toBe(true);
 });
 it('encrypts and authenticates verification capabilities and rejects tampering/expiry',()=>{
  const value={email:'owner@example.com',capability:'PRIVATE-VERIFICATION-CAPABILITY',expires_at:Math.floor(Date.now()/1000)+600};
  const sealed=sealAccountCookie(value);expect(sealed).not.toContain(value.capability);expect(openAccountCookie(sealed)).toEqual(value);
  const changed=Buffer.from(sealed,'base64url');changed[14]^=1;
  expect(openAccountCookie(changed.toString('base64url'))).toBeNull();expect(openAccountCookie(sealAccountCookie({...value,expires_at:1}))).toBeNull();
 });
});
