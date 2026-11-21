import {afterEach,beforeEach,expect,it,vi} from 'vitest';
vi.mock('server-only',()=>({}));
import {verifyChallenge} from '@/lib/server/turnstile';
const form=()=>{const f=new FormData();f.set('cf-turnstile-response','offline-test-token');return f};
beforeEach(()=>{vi.stubEnv('TURNSTILE_ENFORCED','true');vi.stubEnv('TURNSTILE_SITE_KEY','1x00000000000000000000AA');vi.stubEnv('TURNSTILE_SECRET_KEY','1x0000000000000000000000000000000AA')});
afterEach(()=>{vi.unstubAllGlobals();vi.unstubAllEnvs()});
it('requires a token and configured secret before calling Siteverify',async()=>{const call=vi.fn();vi.stubGlobal('fetch',call);expect(await verifyChallenge(new FormData(),'signup')).toBe(false);vi.stubEnv('TURNSTILE_SECRET_KEY','');expect(await verifyChallenge(form(),'signup')).toBe(false);expect(call).not.toHaveBeenCalled()});
it.each([[true,'app.planebyte.com','signup',true],[true,'other.example','signup',false],[true,'app.planebyte.com','recovery',false],[false,'app.planebyte.com','signup',false]])('checks provider success, hostname and action (%s %s %s)',async(success,hostname,action,allowed)=>{vi.stubGlobal('fetch',vi.fn().mockResolvedValue(Response.json({success,hostname,action})));expect(await verifyChallenge(form(),'signup')).toBe(allowed)});
it('fails closed on provider timeout',async()=>{vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new Error('timeout')));expect(await verifyChallenge(form(),'recovery')).toBe(false)});
