import {defineConfig} from '@playwright/test';
import regression from './playwright.intent-radar-regression.config';
const servers=Array.isArray(regression.webServer)?regression.webServer:[];
export default defineConfig({...regression,outputDir:'../data/artifacts/verification/intent-radar-ui/lead-engine',reporter:[['list'],['json',{outputFile:'../data/artifacts/verification/intent-radar-ui/lead-engine-results.json'}]],webServer:servers.map((server,index)=>({...server,env:{...server.env,...(index===1?{HEYSOW_E2E_DIST_DIR:'.next-intent-radar-ui-build'}:{})}}))});
