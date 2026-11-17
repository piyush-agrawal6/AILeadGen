import {it,expect} from 'vitest';
import {isPublicBrandAsset} from '@/lib/auth-policy';
it('allows the exact public commit manifest without opening customer or arbitrary JSON routes',()=>{
 expect(isPublicBrandAsset('/release.json')).toBe(true);
 for(const path of ['/release.json/private','/release.json.bak','/api/release.json','/api/organization/profile','/onboarding','/.env','/customer.json'])expect(isPublicBrandAsset(path)).toBe(false);
});
