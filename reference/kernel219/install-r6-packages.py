"""One native signed APK transaction; record outcome before any recovery."""
from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
assert json.loads((here/'r6-native-preflight-validation.json').read_text())['native_phone_solver_passed']
code=r'''
from pathlib import Path
import hashlib,json,os,stat,subprocess,time
root=Path('/var/lib/samurai');stage=root/'k219-r6-package-candidates';out=root/'k219-r6-package-transaction'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k219-runtime/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert Path('/lib/apk/db/installed').read_bytes()==(out/'installed-before-private.txt').read_bytes()
assert Path('/etc/apk/world').read_bytes()==(out/'world-before-private.txt').read_bytes()
assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in ['/sys/bus/i2c/devices/7-0010','/sys/bus/platform/devices/acb3000.camss','/sys/bus/platform/devices/ac4b000.cci'])
assert all(p.read_text().strip()=='closed' for p in Path('/proc/asound').glob('card*/pcm*/sub*/status'))
marker=out/'transaction-state-private.json';assert not marker.exists()
manifest=json.loads((stage/'forward-manifest.json').read_text());names={p['name'] for p in manifest['packages']};assert len(names)==7
for item in manifest['packages']:assert hashlib.sha256((stage/'forward'/item['file']).read_bytes()).hexdigest()==item['sha256']
state=dict(stage=219,state='submitted',uptime=float(Path('/proc/uptime').read_text().split()[0]),operation='native signed seven-camera-package r6 upgrade')
marker.write_text(json.dumps(state,indent=2)+'\n')
with (out/'native-install-private.log').open('xb') as log:
 p=subprocess.run(['apk','--no-network','--repositories-file',str(out/'candidate-repositories.list'),'add','samurai-camera-stack=0.1.0-r1'],stdout=log,stderr=subprocess.STDOUT,timeout=60)
state.update(state='returned',exit=p.returncode);marker.write_text(json.dumps(state,indent=2)+'\n');assert p.returncode==0
def records(data):
 result={}
 for block in data.decode().split('\n\n'):
  names=[l[2:] for l in block.splitlines() if l.startswith('P:')]
  if names:result[names[0]]=block
 return result
old=records((out/'installed-before-private.txt').read_bytes());new=records(Path('/lib/apk/db/installed').read_bytes())
assert set(old)==set(new) and len(new)==944
assert all(new[name]==block for name,block in old.items() if name not in names)
count=0
for package in manifest['packages']:
 assert 'V:'+package['version'] in new[package['name']].splitlines()
 for relative,item in package['files'].items():
  path=Path('/')/relative
  if item['kind']=='symlink':assert path.is_symlink() and os.readlink(path)==item['target']
  else:assert path.is_file() and not path.is_symlink() and hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256'] and stat.S_IMODE(path.stat().st_mode)==item['mode']
  count+=1
assert stat.S_IMODE(Path('/etc/libcamera').stat().st_mode)==0o755 and not any(Path('/etc/libcamera').glob('*.apk-new'))
assert b'dma_heap: system' in Path('/etc/libcamera/configuration.yaml').read_bytes()
repos=out/'rollback-repositories.list';repos.write_text('ndx file://'+str(root/'k214-package-candidates/forward/packages.adb')+'\n')
previous=json.loads((root/'k214-package-candidates/forward-manifest.json').read_text())
requests=[i['name']+'='+i['version'] for i in previous['packages']]
p=subprocess.run(['apk','--no-network','--repositories-file',str(repos),'add','--simulate',*requests],capture_output=True,text=True,timeout=30)
(out/'native-rollback-dry-private.log').write_text(p.stdout+p.stderr);assert p.returncode==0
actions=[l for l in p.stdout.splitlines() if l.startswith('(')];assert len(actions)==7 and all('Downgrading ' in l for l in actions)
assert all(any(('Downgrading '+i['name']+' (') in l for l in actions) for i in previous['packages'])
repo=Path('/etc/apk/repositories.d/60-samurai-camera.list');repo.write_text('ndx file://'+str(stage/'forward/packages.adb')+'\n');repo.chmod(0o644)
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
state.update(state='verified',installed_package_count=len(new),verified_file_records=count);marker.write_text(json.dumps(state,indent=2)+'\n')
report=dict(stage=219,native_signed_apk_transaction_completed=True,transaction_state='verified',same_boot=True,no_flash_or_reboot=True,
 five_framework_components='99990.7.2-r6',config_and_stack='0.1.0-r1',installed_package_count=944,
 unrelated_937_package_records_unchanged=True,installed_payload_records_hashes_symlinks_and_modes_verified=count,
 product_cpu_config_selects_system_heap=True,native_seven_package_r5_downgrade_simulation_passed=True,
 original_world_repositories_and_r5_payloads_retained=True,taint=0,wireplumber_reload_pending=True,default_capture_verification_pending=True)
(out/'install-summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=110);(host.PRIVATE/'r6-install-host-private.log').write_bytes(p.stdout+p.stderr)
r=json.loads(p.stdout);(here/'r6-package-install-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
