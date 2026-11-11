import {defineConfig} from '@playwright/test';
import regression from './playwright.intent-radar-ui-regression.config';
export default defineConfig({...regression,testDir:'./intent-radar-e2e',outputDir:'../data/artifacts/verification/intent-radar-ui/workflow',reporter:[['list'],['json',{outputFile:'../data/artifacts/verification/intent-radar-ui/workflow-results.json'}]]});
