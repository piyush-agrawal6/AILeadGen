import { defineConfig } from "@playwright/test";
import path from "node:path";
const root=path.resolve(import.meta.dirname,"..");
const python=process.env.LEADENGINE_TEST_PYTHON || (process.platform==="win32"?path.join(root,".venv/Scripts/python.exe"):path.join(root,".venv/bin/python"));
const runId=String(Date.now());
const testEnv={HEYSOW_E2E_DIST_DIR:".next-workflow-test",ENABLE_AI_ACQUISITION:"false",ENABLE_FIRECRAWL_ACQUISITION:"false",ENABLE_LEAD_IMPORT:"false",ENABLE_GOOGLE_SHEETS_IMPORT:"false",GEMINI_API_KEY:"",FIRECRAWL_API_KEY:"",EMAIL_SENDING_ENABLED:"false",AUTO_SCAN_ENABLED:"false",AUTO_EMAIL_ENABLED:"false",EMAIL_SYNC_ENABLED:"false",GMAIL_ENABLED:"false",EMAIL_PROVIDER:"hostinger",MAIL_PASSWORD:"",GMAIL_APP_PASSWORD:"",UPSTASH_REDIS_REST_URL:"",UPSTASH_REDIS_REST_TOKEN:"",MAX_EMAILS_PER_HOUR:"50",MAX_EMAILS_PER_DAY:"500",APP_ENV:"test",ALLOWED_USER_EMAILS:"founder@leadengine.example,cofounder@leadengine.example",AUTH_SECRET:"fixture-session-secret-only-for-local-tests-123456789",LEADENGINE_API_SIGNING_SECRET:"fixture-signing-secret-only-for-local-tests-123456789",AUTH_URL:"http://127.0.0.1:13000",AUTH_DISABLED_LOCAL:"false",LEADENGINE_API_URL:"http://127.0.0.1:18787"};
export default defineConfig({
  testDir:"./e2e",timeout:90000,workers:1,fullyParallel:false,
  outputDir:path.join(root,'data/artifacts/verification/browser-workflow'),
  reporter:[["list"],["html",{open:"never"}]],
  use:{baseURL:"http://127.0.0.1:13000",viewport:{width:1440,height:900},channel:process.env.LEADENGINE_TEST_BROWSER||(process.platform==="win32"?"chrome":undefined),trace:"retain-on-failure",screenshot:"only-on-failure"},
  webServer:[
    {command:'"'+python+'" -m uvicorn app.api.server:app --host 127.0.0.1 --port 18787',cwd:root,url:"http://127.0.0.1:18787/api/health",timeout:60000,env:{...testEnv,DATABASE_PATH:path.join(root,"data/e2e",runId,"phase3.db"),ARTIFACT_LOCAL_ROOT:path.join(root,"data/e2e",runId,"artifacts")}},
    {command:"node node_modules/next/dist/bin/next "+(process.env.LEADENGINE_TEST_DEV?"dev":"start")+" -p 13000",cwd:import.meta.dirname,url:"http://127.0.0.1:13000/login",timeout:60000,env:{...testEnv,HEYSOW_E2E_DIST_DIR:process.env.PLANEBYTE_RELEASE_DIST||testEnv.HEYSOW_E2E_DIST_DIR}},
  ],
});
