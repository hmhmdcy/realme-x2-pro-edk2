"""Install the verified application using a signed, offline, add-only transaction."""
from pathlib import Path
import hashlib
import json
import host

R=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((R/'snapshot-relay-validation.json').read_text())['native_phone_original_trusted_keys_verified']
index=P/'snapshot-distro-apks/packages.adb';digest=hashlib.sha256(index.read_bytes()).hexdigest()
host.upload(index,'/var/lib/samurai/k240-snapshot-host-packages/apks/packages.adb')
code=r'''
from pathlib import Path
import hashlib,json,os,re,subprocess,sys
os.umask(0o077);r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
candidate=r/'k240-snapshot-host-packages';assert json.loads((candidate/'summary.json').read_text())['native_phone_original_trusted_keys_verified']
assert hashlib.sha256((candidate/'apks/packages.adb').read_bytes()).hexdigest()==sys.argv[1]
p=subprocess.run(['apk','verify',str(candidate/'apks/packages.adb')],capture_output=True,timeout=15);assert p.returncode==0
out=r/'k240-snapshot-app-transaction';assert not out.exists();out.mkdir(mode=0o700)
before=Path('/lib/apk/db/installed').read_bytes();world=Path('/etc/apk/world').read_bytes()
assert before==(candidate/'installed-before-private.txt').read_bytes() and world==(candidate/'world-before-private.txt').read_bytes()
(out/'installed-before-private.txt').write_bytes(before);(out/'world-before-private.txt').write_bytes(world)
repo=out/'candidate-repositories.list';repo.write_text('ndx file://'+str(candidate/'apks/packages.adb')+'\n')
manifest=json.loads((candidate/'manifest.json').read_text());expected={i['name']:i['version'] for i in manifest['packages']};assert len(expected)==14
request=['apk','--no-network','--repositories-file',str(repo),'add','snapshot=51.0-r0']
p=subprocess.run([*request,'--simulate'],capture_output=True,text=True,timeout=30)
(out/'forward-simulation-private.log').write_text(p.stdout+p.stderr);assert p.returncode==0
actions=[line for line in p.stdout.splitlines() if re.match(r'^\(\s*\d+/\d+\)',line)]
assert len(actions)==14 and all('Installing ' in line for line in actions)
for name,version in expected.items():assert any(('Installing '+name+' ('+version+')') in line for line in actions)
state=dict(stage=240,state='submitted',operation='native offline signed add-only Snapshot51 application')
(out/'transaction-state-private.json').write_text(json.dumps(state,indent=2)+'\n')
with (out/'install-private.log').open('xb') as log:p=subprocess.run(request,stdout=log,stderr=subprocess.STDOUT,timeout=75)
state.update(state='returned',exit_code=p.returncode);(out/'transaction-state-private.json').write_text(json.dumps(state,indent=2)+'\n');assert p.returncode==0
def records(data):
 result={}
 for block in data.decode().split('\n\n'):
  names=[l[2:] for l in block.splitlines() if l.startswith('P:')]
  if names:assert len(names)==1;result[names[0]]=block
 return result
old=records(before);new=records(Path('/lib/apk/db/installed').read_bytes());assert len(old)==944 and len(new)==958
assert set(new)-set(old)==set(expected) and all(new[n]==v for n,v in old.items())
assert all('V:'+version in new[name].splitlines() for name,version in expected.items())
assert set(Path('/etc/apk/world').read_text().splitlines())==set(world.decode().splitlines())|{'snapshot=51.0-r0'}
camera=json.loads((r/'k239-r15-package-candidates/forward-manifest.json').read_text());count=0
for package in camera['packages']:
 for relative,item in package['files'].items():
  path=Path('/')/relative
  if item['kind']=='symlink':assert path.is_symlink() and os.readlink(path)==item['target']
  else:assert hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']
  count+=1
assert count==49
p=subprocess.run(['apk','--no-network','--repositories-file',str(repo),'del','--simulate','snapshot'],capture_output=True,text=True,timeout=30)
(out/'rollback-simulation-private.log').write_text(p.stdout+p.stderr);assert p.returncode==0
removals=[line for line in p.stdout.splitlines() if re.match(r'^\(\s*\d+/\d+\)',line)]
assert len(removals)==14 and all('Purging ' in line for line in removals)
for name in expected:assert any(('Purging '+name+' (') in line for line in removals)
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
state.update(state='verified',old_records_unchanged=944,new_packages=14,package_total=958)
(out/'transaction-state-private.json').write_text(json.dumps(state,indent=2)+'\n')
report=dict(stage=240,snapshot_version='51.0-r0',signed_offline_native_install_completed=True,
 added_packages=14,installed_package_total=958,all944_previous_package_records_unchanged=True,
 r15_r10_camera49_payload_records_unchanged=True,world_only_added_pinned_snapshot=True,
 native_remove_snapshot_simulation_returns_exact14_additions=True,no_kernel_or_boot_change=True,
 taint=0,gui_preview_not_yet_verified=True,default_launcher_not_changed=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
p=P/'current-work-private.json';state=json.loads(p.read_text());state.update(state='Signed Snapshot14 add-only native transaction about to be submitted',active_native_context='/var/lib/samurai/k240-snapshot-app-transaction',next='Observe same install handle/state; do not repeat unknown outcome. Then inspect actual GUI/PipeWire path.')
p.write_text(json.dumps(state,indent=2)+'\n')
result=host.ssh('python3 - '+digest,input=code.encode(),timeout=150)
(P/'snapshot-install-host-private.log').write_bytes(result.stdout+result.stderr)
report=json.loads(result.stdout);(R/'snapshot-install-validation.json').write_text(json.dumps(report,indent=2)+'\n')
state=json.loads(p.read_text());state.update(state='Snapshot51 installed14 additions, old944/r15 payload unchanged; GUI pending',active_native_context=None,snapshot_installed=True,next='Inspect exact PipeWire video devices, launch Snapshot with known camera, verify frames/default r15 maps and complete exit cleanup')
p.write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(report))
