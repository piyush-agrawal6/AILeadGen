// Keep npm's standard development entry point on the same isolated launcher.
// Authentication/environment handling has one implementation in local_preview.py.
const path = require('node:path');
const {spawn} = require('node:child_process');
const root = path.resolve(__dirname, '..');
const python = path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const child = spawn(python, [path.join(__dirname, 'local_preview.py'), 'frontend'], {cwd:root, env:process.env, stdio:'inherit'});
child.on('error', () => {console.error('The local preview needs the project Python .venv. See docs/HEYSOW_OPERATIONS.md.');process.exitCode=1});
for (const signal of ['SIGINT','SIGTERM']) process.on(signal,()=>child.kill(signal));
child.on('exit',(code)=>{process.exitCode=code ?? 1});
