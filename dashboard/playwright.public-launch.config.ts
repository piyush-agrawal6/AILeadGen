import {defineConfig} from '@playwright/test';
import base from './playwright.accounts.config';
export default defineConfig({...base,testDir:'./intent-radar23-e2e',testMatch:'product-overhaul.spec.ts',outputDir:'../data/artifacts/verification/public-launch/product-browser',reporter:[['list'],['json',{outputFile:'../data/artifacts/verification/public-launch/product-browser.json'}]]});
