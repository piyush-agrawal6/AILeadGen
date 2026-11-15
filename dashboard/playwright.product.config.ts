import {defineConfig} from '@playwright/test';
import base from './playwright.intent-only.config';
export default defineConfig({...base,testMatch:'product-overhaul.spec.ts',outputDir:'../data/artifacts/verification/final-remediation/browser',reporter:[['list'],['json',{outputFile:'../data/artifacts/verification/final-remediation/browser-results.json'}]]});
