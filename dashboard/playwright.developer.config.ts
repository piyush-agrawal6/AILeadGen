import {defineConfig} from '@playwright/test';
import base from './playwright.config';
const servers=Array.isArray(base.webServer)?base.webServer:base.webServer?[base.webServer]:[];
export default defineConfig({...base,testDir:'./developer-e2e',outputDir:'../data/artifacts/verification/browser-developer',webServer:servers.map(server=>({...server,env:{...server.env,MCP_ALLOWED_HOSTS:'127.0.0.1:18787',MCP_ALLOWED_ORIGINS:'http://127.0.0.1:13000',HEYSOW_WORKSPACE_MANAGEMENT_ENABLED:'true',HEYSOW_DEVELOPER_API_ENABLED:'true',HEYSOW_MCP_ENABLED:'true',HEYSOW_WEBHOOKS_ENABLED:'true',HEYSOW_INTEGRATION_ENCRYPTION_KEY:'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='}}))});
