import {defineConfig} from '@playwright/test';
import base from './playwright.config';
const servers=Array.isArray(base.webServer)?base.webServer:base.webServer?[base.webServer]:[];
export default defineConfig({...base,testDir:'./workspace-e2e',outputDir:'../data/artifacts/verification/browser-workspace',webServer:servers.map((server,i)=>({...server,command:i?server.command:server.command.replace('app.api.server:app','tests.workspace_release_fixture_server:app'),env:{...server.env,LEAD_ENGINE_AVAILABLE:'true',INTENT_RADAR_STAGE:'Beta',HEYSOW_WORKSPACE_MANAGEMENT_ENABLED:'true',ALLOWED_USER_EMAILS:'founder@leadengine.example,cofounder@leadengine.example,recipient@example.com,ui@leadengine.example'}}))});
