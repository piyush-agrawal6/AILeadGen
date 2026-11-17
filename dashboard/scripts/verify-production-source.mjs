import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
// The existing Vercel project invokes this before building. Old snapshots lacking
// the guard or a prepared source manifest cannot replace the integrated release.
if(process.env.VERCEL_ENV==='production'||process.argv.includes('--require')){
 const root=process.cwd();
 const policy=JSON.parse(readFileSync(resolve(root,'release-policy.json'),'utf8'));
 const release=JSON.parse(readFileSync(resolve(root,'public/release.json'),'utf8'));
 if(release.branch!==policy.branch||release.ui_baseline!==policy.ui_baseline||release.backend_baseline!==policy.backend_baseline||!/^[a-f0-9]{40}$/.test(release.source_commit)||!/^[a-f0-9]{40}$/.test(release.frontend_tree))throw new Error('Production source is not the prepared integrated release. Use scripts/prepare_frontend_release.py.');
 console.log('Verified integrated production source '+release.source_commit);
}
