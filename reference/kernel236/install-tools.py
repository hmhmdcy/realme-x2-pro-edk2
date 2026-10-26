"""Install exact transition/observer sources; no quiesce or transition yet."""
from pathlib import Path
import hashlib
import json
import host

R = Path(__file__).resolve().parent
P = host.PRIVATE
code = '''from pathlib import Path
import json
root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k233-runtime/boot-id-private.txt').read_bytes()==(root/'k236-baseline/boot-id-private.txt').read_bytes()
assert json.loads((root/'k235-module-stage/transaction-state-private.json').read_text())['state']=='verified'
out=root/'k236-tools';assert not out.exists();out.mkdir(mode=0o700)
print('FRESH_TOOLS_CREATED')
'''
result = host.ssh('python3 -', input=code.encode(), timeout=15)
(P / 'tools-create-private.log').write_bytes(result.stdout + result.stderr)
host.upload(P / 'deployment-lock-private.json', '/var/lib/samurai/k236-tools/deployment-lock-private.json')
manifest = {}
for name in ['quiesce-current183.sh', 'stop-gnss-idle.py', 'quiesce-camera.py', 'disable-crtc.py',
             'check-quiesce.py', 'freeze-for-bootloader.sh', 'linux-restart2-bootloader.py',
             'preflight-transition.py', 'collect-newboot.py']:
    dest = '/var/lib/samurai/k236-tools/' + name if name in ['linux-restart2-bootloader.py', 'preflight-transition.py', 'collect-newboot.py'] else '/tmp/k236-' + name
    host.upload(R / name, dest)
    manifest[dest] = hashlib.sha256((R / name).read_bytes()).hexdigest()
path = P / 'uploaded-sources-private.json'
path.write_text(json.dumps(manifest, indent=2) + '\n')
host.upload(path, '/var/lib/samurai/k236-tools/uploaded-sources-private.json')
code = '''from pathlib import Path
import hashlib,json,subprocess
root=Path('/var/lib/samurai');before=root/'k236-baseline'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(before/'boot-id-private.txt').read_bytes()
for name,digest in json.loads((root/'k236-tools/uploaded-sources-private.json').read_text()).items():
 p=Path(name);assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
 if p.suffix=='.py':compile(p.read_text(),name,'exec')
 else:subprocess.run(['sh','-n',name],check=True)
parts=(before/'partition-check.sha256').read_text().splitlines();assert len(parts)==3
lock=json.loads((root/'k236-tools/deployment-lock-private.json').read_text())
assert sum(line==lock['files']['boot232_rollback']['sha256']+'  /dev/sde11' for line in parts)==1
candidate=lock['files']['boot_candidate']['sha256']
(root/'k236-tools/partition-after.sha256').write_text(''.join((candidate+'  /dev/sde11' if line.endswith('  /dev/sde11') else line)+'\\n' for line in parts))
assert Path('/sys/module/qcom_pm8008/notes/.note.gnu.build-id').read_bytes()==(before/'mfd-loaded-note-private.bin').read_bytes()
assert Path('/sys/module/reset_realme_rmx1931_pm8008').exists()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
print(json.dumps(dict(stage=236,uploaded_tools=9,exact_paths_hashes_syntax_verified=True,pre_post_boot_manifests_split=True,live_p_q_provider_retained=True)))
'''
result = host.ssh('python3 -', input=code.encode(), timeout=25)
(P / 'tools-check-private.log').write_bytes(result.stdout + result.stderr)
report = json.loads(result.stdout)
(R / 'tools-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
