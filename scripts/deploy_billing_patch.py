"""Ship a verified schema-46 billing patch on existing API/worker resources only.

Image-only updates preserve identities, environment/secret references, commands,
flags and schedulers. No migrations, data cleanup or provider payment actions.
"""
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from scripts.deploy_beta_backend import command, REGION
from scripts.deploy_growth_release import spec
from scripts.deploy_billing_release import read_smoke

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/artifacts/verification/razorpay'
RESOURCES = [('services', 'leadengine-api', 'api'),
             ('jobs', 'leadengine-worker', 'worker'),
             ('jobs', 'leadengine-acquisition', 'worker'),
             ('jobs', 'leadengine-quota-canary', 'worker')]


def main():
    frozen = json.loads((OUT / 'billing-history-codehash.json').read_text())
    digest = hashlib.sha256()
    for path in sorted((ROOT / 'app').rglob('*.py')):
        digest.update(str(path.relative_to(ROOT)).encode() + b'\0' + path.read_bytes() + b'\0')
    suites = ET.parse(OUT.parent / frozen['test_report']).getroot()
    suites = list(suites) if suites.tag == 'testsuites' else [suites]
    if digest.hexdigest() != frozen['app_sha256'] or sum(int(s.get('tests', 0)) for s in suites) < 960 or any(int(s.get('failures', 0)) + int(s.get('errors', 0)) for s in suites):
        raise RuntimeError('The full isolated suite must pass against this exact backend source.')
    source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    build = json.loads((OUT / 'build.json').read_text())
    verified = command(['builds', 'describe', build['build_id']])
    if build['source_commit'] != source or verified['status'] != 'SUCCESS' or verified['substitutions']['_SOURCE_REV'] != source:
        raise RuntimeError('The exact committed patch images must be built successfully first.')
    log = (OUT.parent / 'billing-terminal-regression.log').read_text()
    if 'failed' in log or 'error' in log.lower() or 'passed' not in log:
        raise RuntimeError('Billing and release-security regression checks must pass.')
    folder = ROOT / 'data/backups' / ('billing-patch-' + source[:10])
    folder.mkdir(mode=0o700, exist_ok=False)

    def save(name, value):
        path = folder / (name + '.json')
        path.write_text(json.dumps(value, indent=2))
        path.chmod(0o600)

    previous = {}
    for kind, name, _ in RESOURCES:
        previous[name] = command(['run', kind, 'describe', name, '--region=' + REGION])
        save(name + '-before', previous[name])
    schedules = command(['scheduler', 'jobs', 'list', '--location=' + REGION])
    save('schedulers-before', schedules)

    def update(kind, name, image):
        before = spec(previous[name], kind)
        env = {x['name']: x for x in before['containers'][0].get('env', [])}
        for key in ('AUTO_SCAN_ENABLED', 'AUTO_EMAIL_ENABLED', 'EMAIL_SENDING_ENABLED', 'HEYSOW_PUBLIC_REGISTRATION_ENABLED', 'BILLING_PUBLIC_CHECKOUT_ENABLED'):
            if env.get(key, {}).get('value') != 'false':
                raise RuntimeError('A production safety guard changed; no image update performed.')
        if env.get('RAZORPAY_MODE', {}).get('value') != 'test':
            raise RuntimeError('Only the existing restricted Test Mode is permitted.')
        args = ['run', kind, 'update', name, '--region=' + REGION, '--image=' + image]
        if kind == 'services':
            args += ['--no-traffic', '--tag=billing-patch']
        result = command(args)
        after = spec(result, kind)
        # Only the image may differ inside the application runtime specification.
        for item in (before, after):
            item['containers'][0].pop('image', None)
        if before != after:
            raise RuntimeError('An unrelated runtime setting changed; inspect the restricted checkpoint.')
        save(name + '-updated', result)
        return result

    api = update('services', 'leadengine-api', build['api_image'])
    revision = api['status']['latestReadyRevisionName']
    if revision != api['status']['latestCreatedRevisionName']:
        raise RuntimeError('The patch revision is not ready; existing traffic remains unchanged.')
    smoke = read_smoke('https://billing-patch---leadengine-api-befca7xg4a-el.a.run.app')
    for kind, name, image in RESOURCES:
        if kind == 'jobs':
            update(kind, name, build[image + '_image'])
    command(['run', 'services', 'update-traffic', 'leadengine-api', '--region=' + REGION, '--to-revisions=' + revision + '=100'])
    after_schedules = command(['scheduler', 'jobs', 'list', '--location=' + REGION])
    if schedules != after_schedules:
        # Runtime scheduler timestamps can change independently. Configuration and
        # state must remain identical; no scheduler mutation is performed here.
        def settings(rows):
            return {r['name']: {k: v for k, v in r.items() if k not in ('lastAttemptTime', 'status', 'scheduleTime', 'userUpdateTime')} for r in rows}
        if settings(schedules) != settings(after_schedules):
            raise RuntimeError('Scheduler configuration changed concurrently; inspect before proceeding.')
    proof = {'source_commit': source, 'revision': revision, 'schema': 46,
             'migration_run': False, 'image_only': True, 'safety_settings_preserved': True,
             'smoke': smoke, 'public_checkout': False, 'live_payments': False}
    save('promoted', proof)
    (OUT / 'patch-promoted.json').write_text(json.dumps(proof, indent=2))
    (OUT / 'patch-promoted.json').chmod(0o600)
    print(json.dumps(proof))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'status': 'BLOCKED', 'error_type': type(error).__name__,
                          'detail': str(error) if isinstance(error, RuntimeError) else 'Inspect the private patch checkpoint; credentials withheld.'}))
        raise SystemExit(1)
