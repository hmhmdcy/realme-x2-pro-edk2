"""Replace only the charger module/manifest; retain USB and protection.
No original high-current register rollback is used on the current SDP source.
"""
from pathlib import Path
import base64
import hashlib
import json
import os
import runpy
import subprocess
import sys
import time
import traceback

os.umask(0o077)
request = json.loads(sys.stdin.buffer.read())
assert request['transaction'] == 'ui-update-r2'
out = Path('/root/charging-management-20261023') / request['transaction']; out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == Path(request['guard']).read_bytes()
manager = runpy.run_path('/usr/sbin/samurai-charging'); live = manager['live']
assert manager['verify']() == request['old_manifest']
before = live.state(); assert before['taint'] == '0'
(out / 'before-private.json').write_text(json.dumps(before))
backup, new = {}, {}
for name, encoded in request['files'].items():
    target = Path(name)
    assert name in [request['new_manifest']['modules']['samurai-mp2650']['target'], '/usr/share/samurai-charging/manifest.json']
    backup[target] = target.read_bytes(); new[target] = base64.b64decode(encoded)
    (out / (target.name + '.before')).write_bytes(backup[target])
    if target.name.endswith('.ko'):
        assert hashlib.sha256(new[target]).hexdigest() == request['new_manifest']['installed_files'][name]
    else:
        assert json.loads(new[target]) == request['new_manifest']

def write(target, content):
    tmp = target.with_name(target.name + '.ui-update-next'); assert not tmp.exists()
    with tmp.open('xb') as stream: stream.write(content); stream.flush(); os.fsync(stream.fileno())
    tmp.chmod(0o600); tmp.replace(target)

def command(*args):
    response = subprocess.run(args, capture_output=True, text=True, timeout=30)
    with (out / 'commands-private.log').open('a') as stream: stream.write(repr(args) + '\n' + response.stdout + response.stderr)
    assert response.returncode == 0, (args, response.returncode)

failure = recovery = None
try:
    command('rc-service', 'samurai-charging', 'stop')
    command('rmmod', 'samurai_mp2650')
    assert not (live.CLIENT / 'driver').exists()
    for target, content in new.items(): write(target, content)
    command('depmod', '-a', os.uname().release)
    manager['load_module'](request['new_manifest'], 'samurai-mp2650', ['runtime_board=1', 'control=1'])
    command('rc-service', 'samurai-charging', 'start'); time.sleep(2)
    assert manager['verify']() == request['new_manifest']
    for name, entry in request['new_manifest']['modules'].items():
        manager['loaded_matches'](Path(entry['target']), name.replace('-', '_'))
    sample = manager['sample']()
    assert sample['valid'] == sample['protection_ok'] == sample['desired_enable'] == 1
    assert not any(sample[k] for k in ['error', 'stop_error', 'latched', 'source_inhibit', 'fault'])
except BaseException:
    failure = traceback.format_exc()
    try:
        if (live.CLIENT / 'driver').exists(): command('rc-service', 'samurai-charging', 'stop')
        if Path('/sys/module/samurai_mp2650').exists(): command('rmmod', 'samurai_mp2650')
        for target, content in backup.items(): write(target, content)
        command('depmod', '-a', os.uname().release)
        manager['load_module'](request['old_manifest'], 'samurai-mp2650', ['runtime_board=1', 'control=1'])
        command('rc-service', 'samurai-charging', 'start')
    except BaseException:
        recovery = traceback.format_exc()
after = live.state(); (out / 'after-private.json').write_text(json.dumps(after))
same = all(before[key] == after[key] for key in ['camera_pm', 'm2m', 'services'])
result = {'passed': not failure and not recovery and same and after['taint'] == '0',
          'terminal': True, 'taint': int(after['taint']), 'camera_services_unchanged': same,
          'native_usb_and_protection_kept_loaded': True,
          'gauge_notification_link_registered': not failure,
          'new_manifest_sha256': hashlib.sha256(Path('/usr/share/samurai-charging/manifest.json').read_bytes()).hexdigest(),
          'sample': manager['sample']() if (live.CLIENT / 'driver').resolve().name == 'samurai-mp2650' else None}
(out / 'failure-private.json').write_text(json.dumps({'update': failure, 'recovery': recovery}))
(out / 'result.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result), flush=True)
if not result['passed']: raise SystemExit(1)
