import {beforeEach,expect,it,vi} from 'vitest';
const state=vi.hoisted(()=>({session:null as any,result:{ok:false,data:{}} as any,request:vi.fn(),env:{accounts:true,customerAccess:true,production:true,allowed:['owner@example.com']}}));
vi.mock('server-only',()=>({}));
vi.mock('react',()=>({cache:(fn:any)=>fn}));
vi.mock('@/auth',()=>({auth:async()=>state.session}));
vi.mock('@/lib/server/private-session',()=>({privateSession:async()=>'private-capability'}));
vi.mock('@/lib/server/env',()=>({serverEnv:()=>state.env}));
vi.mock('@/lib/server/account-broker',()=>({accountRequest:state.request}));
import {currentUser} from '@/lib/server/session';
beforeEach(()=>{state.request.mockReset();state.request.mockResolvedValue({ok:false,data:{}})});
it('denies old allowlisted OAuth JWTs without backend admission',async()=>{
 state.session={user:{email:'owner@example.com'}};expect(await currentUser()).toBeNull();expect(state.request).not.toHaveBeenCalled();
});
it('denies removed accounts even if the JWT and allowlist remain',async()=>{
 state.session={user:{email:'owner@example.com',planeByteAdmitted:true}};expect(await currentUser()).toBeNull();expect(state.request).toHaveBeenCalledWith('session','owner@example.com',{},'private-capability');
});
it('denies personal identities before private account access',async()=>{
 state.session={user:{email:'owner@gmail.com',planeByteAdmitted:true}};expect(await currentUser()).toBeNull();expect(state.request).not.toHaveBeenCalled();
});
