import {expect,type BrowserContext} from '@playwright/test';
import type {WorkspaceSummary} from '../components/workspaces/use-workspace';

/** Exercise account selection with the real membership and creation endpoints. */
export async function createInFixtureAccount(context:BrowserContext,name:string,accountWorkspace:string){
  const path='/api/organization/workspaces',headers={origin:'http://127.0.0.1:13000'};
  async function memberships():Promise<WorkspaceSummary>{const r=await context.request.get(path);expect(r.status()).toBe(200);return r.json()}
  const before=await memberships();
  const target=before.items.find(item=>item.name===accountWorkspace);
  expect(target?.role).toBe('OWNER');
  const account=target?.billing_account, data={name,request_id:crypto.randomUUID()};
  if(process.env.SHARED_BILLING_ACCOUNTS_ENABLED==='true'){
    expect(account?.can_manage).toBe(true);
    expect(account?.can_select_at_creation).toBe(true);
  }
  const r=await context.request.post(path,{headers,data:{...data,...(account?{billing_account_id:account.id}:{})}});
  expect(r.status(),await r.text()).toBe(201);
  if(account){const created=await r.json(),after=await memberships();expect(after.active_organization_id).toBe(created.organization_id);expect(after.items.find(i=>i.organization_id===created.organization_id)?.billing_account).toMatchObject({id:account.id,shared:true});}
}
