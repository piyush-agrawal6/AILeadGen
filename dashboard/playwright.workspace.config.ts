import {defineConfig} from '@playwright/test';
import base from './playwright.config';
const servers=Array.isArray(base.webServer)?base.webServer:base.webServer?[base.webServer]:[];
export default defineConfig({...base,testDir:'./workspace-e2e',outputDir:'../data/artifacts/verification/browser-workspace',webServer:servers.map(server=>({...server,env:{...server.env,HEYSOW_WORKSPACE_MANAGEMENT_ENABLED:'true',ALLOWED_USER_EMAILS:'founder@leadengine.example,cofounder@leadengine.example,ui@leadengine.example'}}))});
