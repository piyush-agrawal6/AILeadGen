import {defineConfig} from '@playwright/test';
import auth from './playwright.auth.config';
import workspace from './playwright.workspace.config';
import integrations from './playwright.integrations.config';
import ui from './playwright.intent-radar-ui.config';
const suite=process.env.RADAR23_PLATFORM_SUITE || 'auth';
const bases={auth,workspace,integrations,ui};
if(!(suite in bases))throw new Error('Unknown Phase 2/3 platform regression suite');
const base=bases[suite as keyof typeof bases];
const servers=Array.isArray(base.webServer)?base.webServer:base.webServer?[base.webServer]:[];
export default defineConfig({...base,use:{...base.use,channel:undefined},
 outputDir:`../data/artifacts/verification/intent-radar23-platform-${suite}`,
 reporter:[['list'],['json',{outputFile:`../data/artifacts/verification/intent-radar23-platform-${suite}-results.json`}]],
 webServer:servers.map(s=>({...s,...(s.command?.startsWith('node ')?{
  command:`node ../scripts/local_frontend.cjs start -p ${suite==='auth'?'13001':suite==='ui'?'14040':'13000'}`,
  env:{...s.env,HEYSOW_E2E_DIST_DIR:'.next-intent-radar23-build'},
 }:{env:{...s.env,DATABASE_BACKEND:'sqlite',DATABASE_URL:''}})})),
});
