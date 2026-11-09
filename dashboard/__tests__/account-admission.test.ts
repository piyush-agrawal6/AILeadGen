import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest';
import {randomUUID} from 'node:crypto';
const mocks=vi.hoisted(()=>({env:{production:false,apiUrl:'http://127.0.0.1:8787',secret:'synthetic-admission-secret-at-least-32-characters',allowed:[],publicRegistration:true,customerAccess:true,termsVersion:'synthetic-review-version'},get:vi.fn(),remove:vi.fn(),set:vi.fn()}));
vi.mock('server-only',()=>({}));
vi.mock('next/headers',()=>({cookies:async()=>({get:mocks.get,delete:mocks.remove,set:mocks.set})}));
vi.mock('@/lib/server/env',()=>({serverEnv:()=>mocks.env}));
import {admitGoogle,decodeConsent,encodeConsent} from '@/lib/server/admission';

beforeEach(()=>{vi.restoreAllMocks();mocks.get.mockReset();mocks.remove.mockReset();mocks.set.mockReset();mocks.env.customerAccess=true;vi.stubEnv('AUTH_GOOGLE_ID','synthetic-google-client')});
afterEach(()=>{vi.unstubAllGlobals();vi.unstubAllEnvs()});
describe('signed consent and Google admission',()=>{
  it('rejects tampered, expired and future consent',()=>{
    const ticket={version:mocks.env.termsVersion,accepted_at:Math.floor(Date.now()/1000),nonce:randomUUID()};
    const encoded=encodeConsent(ticket,mocks.env.secret);
    expect(decodeConsent(encoded,mocks.env.secret)).toEqual(ticket);
    expect(decodeConsent(encoded.slice(0,-1)+(encoded.endsWith('0')?'1':'0'),mocks.env.secret)).toBeNull();
    expect(decodeConsent(encodeConsent({...ticket,accepted_at:ticket.accepted_at-700},mocks.env.secret),mocks.env.secret)).toBeNull();
    expect(decodeConsent(encodeConsent({...ticket,accepted_at:ticket.accepted_at+100},mocks.env.secret),mocks.env.secret)).toBeNull();
  });
  it('does not contact the broker for unverified or disabled account admission',async()=>{
    const send=vi.fn();vi.stubGlobal('fetch',send);
    expect(await admitGoogle({email:'new@example.test',sub:'verified-subject',email_verified:false})).toBe(false);
    mocks.env.customerAccess=false;
    expect(await admitGoogle({email:'new@example.test',sub:'verified-subject',email_verified:true})).toBe(false);
    expect(send).not.toHaveBeenCalled();
  });
  it('sends bounded signed claims and consumes consent only after matching account success',async()=>{
    const nonce=randomUUID();mocks.get.mockReturnValue({value:encodeConsent({version:mocks.env.termsVersion,accepted_at:Math.floor(Date.now()/1000),nonce},mocks.env.secret)});
    const send=vi.fn().mockResolvedValue(Response.json({user_id:'new@example.test',status:'ACTIVE'}));vi.stubGlobal('fetch',send);
    expect(await admitGoogle({email:'NEW@example.test',sub:'verified-subject',email_verified:true})).toBe(true);
    const [url,request]=send.mock.calls[0];expect(url).toBe('http://127.0.0.1:8787/api/organization/admission/google');
    expect(request.cache).toBe('no-store');expect(request.redirect).toBe('error');
    expect(JSON.parse(request.body)).toMatchObject({email:'new@example.test',google_subject:'verified-subject',acceptance_nonce:nonce,client_id:'synthetic-google-client'});
    expect(request.headers['x-le-signature']).toMatch(/^[a-f0-9]{64}$/);expect(mocks.remove).toHaveBeenCalledOnce();
  });
  it('fails closed on wrong account, rejection and transport failure',async()=>{
    for(const response of [Response.json({user_id:'foreign@example.test',status:'ACTIVE'}),new Response('',{status:403})]){
      vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response));
      expect(await admitGoogle({email:'new@example.test',sub:'verified-subject',email_verified:true})).toBe(false);
    }
    vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new Error('Synthetic connection failure')));
    expect(await admitGoogle({email:'new@example.test',sub:'verified-subject',email_verified:true})).toBe(false);expect(mocks.remove).not.toHaveBeenCalled();
  });
  it('preserves the signed private invitation for explicit review, without putting it in redirect URLs',async()=>{
    const ticket={version:mocks.env.termsVersion,accepted_at:Math.floor(Date.now()/1000),nonce:randomUUID(),invitation_token:'private-invitation-token-'.padEnd(43,'x')};
    mocks.get.mockReturnValue({value:encodeConsent(ticket,mocks.env.secret)});
    const send=vi.fn().mockResolvedValue(Response.json({user_id:'new@example.test',status:'ACTIVE'}));vi.stubGlobal('fetch',send);
    expect(await admitGoogle({email:'new@example.test',sub:'verified-subject',email_verified:true})).toBe(true);
    const [url,request]=send.mock.calls[0];expect(url).not.toContain(ticket.invitation_token);
    expect(JSON.parse(request.body).invitation_token).toBe(ticket.invitation_token);
    expect(mocks.set).toHaveBeenCalledWith('planebyte-invitation-review',expect.any(String),expect.objectContaining({httpOnly:true,path:'/accept-invitation',sameSite:'lax',maxAge:600}));
    expect(decodeConsent(mocks.set.mock.calls[0][1],mocks.env.secret)).toEqual(ticket);
    expect(mocks.remove).toHaveBeenCalledOnce();
    expect(decodeConsent(encodeConsent({...ticket,invitation_token:'invalid'},mocks.env.secret),mocks.env.secret)).toBeNull();
  });
});
