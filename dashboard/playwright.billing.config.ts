import {defineConfig} from '@playwright/test';
import base from './playwright.growth.config';
const servers=Array.isArray(base.webServer)?base.webServer:[];
export default defineConfig({...base,testMatch:'billing.spec.ts',outputDir:'../data/artifacts/verification/billing-browser',reporter:[['list'],['json',{outputFile:'../data/artifacts/verification/billing-browser-results.json'}]],webServer:servers.map((server,index)=>({...server,command:index===0?server.command.replace('tests.growth_fixture_server:app','tests.billing_fixture_server:app'):server.command}))});
