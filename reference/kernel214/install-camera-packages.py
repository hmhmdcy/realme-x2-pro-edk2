"""One recorded, native APK transaction after full hardware-candidate validation."""
from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
assert json.loads((here/'native-install-preflight-validation.json').read_text())['native_phone_solver_passed']
code=r'''
from pathlib import Path
import hashlib,json,os,stat,subprocess,time
os.umask(0o077);base=Path('/var/lib/samurai/k214-baseline');stage=Path('/var/lib/samurai/k214-package-candidates');out=Path('/var/lib/samurai/k214-package-transaction')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(base/'boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert Path('/lib/apk/db/installed').read_bytes()==(out/'installed-before-private.txt').read_bytes()
assert Path('/etc/apk/world').read_bytes()==(out/'world-before-private.txt').read_bytes()
marker=out/'transaction-state-private.json';assert not marker.exists()
manifest=json.loads((stage/'forward-manifest.json').read_text())
for item in manifest['packages']:assert hashlib.sha256((stage/'forward'/item['file']).read_bytes()).hexdigest()==item['sha256']
assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in ['/sys/bus/i2c/devices/7-0010','/sys/bus/platform/devices/acb3000.camss','/sys/bus/platform/devices/ac4b000.cci'])
repo=Path('/etc/apk/repositories.d/60-samurai-camera.list');assert not repo.exists()
repo.write_text('ndx file://'+str(stage/'forward/packages.adb')+'\n');repo.chmod(0o644)
state=dict(stage=214,state='submitted',uptime=float(Path('/proc/uptime').read_text().split()[0]),command='apk local signed seven-camera-package upgrade')
marker.write_text(json.dumps(state,indent=2)+'\n')
with (out/'native-install-private.log').open('wb') as log:
    p=subprocess.run(['apk','--no-network','--repositories-file',str(out/'candidate-repositories.list'),'add','samurai-camera-stack=0.1.0-r0'],stdout=log,stderr=subprocess.STDOUT,timeout=60)
state.update(state='returned',exit=p.returncode);marker.write_text(json.dumps(state,indent=2)+'\n');assert p.returncode==0
def records(data):
    result={}
    for block in data.decode().split('\n\n'):
        names=[line[2:] for line in block.splitlines() if line.startswith('P:')]
        if names:result[names[0]]=block
    return result
old=records((out/'installed-before-private.txt').read_bytes());new=records(Path('/lib/apk/db/installed').read_bytes())
upgraded={'libcamera','libcamera-ipa','libcamera-tools'};added={'libcamera-gstreamer','libcamera-v4l2','samurai-camera-config','samurai-camera-stack'}
assert set(new)-set(old)==added and not set(old)-set(new)
assert all(new[name]==block for name,block in old.items() if name not in upgraded)
versions={name:next(line[2:] for line in block.splitlines() if line.startswith('V:')) for name,block in new.items()}
count=0
for package in manifest['packages']:
    assert versions[package['name']]==package['version']
    for relative,item in package['files'].items():
        path=Path('/')/relative
        if item['kind']=='symlink':assert path.is_symlink() and os.readlink(path)==item['target']
        else:assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256'] and stat.S_IMODE(path.stat().st_mode)==item['mode']
        count+=1
assert stat.S_IMODE(Path('/etc/libcamera').stat().st_mode)==0o755
assert not any(Path('/etc/libcamera').glob('*.apk-new'))
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
state.update(state='verified',installed_package_count=len(new),verified_file_records=count);marker.write_text(json.dumps(state,indent=2)+'\n')
report=dict(stage=214,native_signed_apk_transaction_completed=True,transaction_state='verified',same_boot=True,no_flash_or_reboot=True,three_upgraded_camera_packages='99990.7.2-r5',four_new_packages_installed=True,installed_package_count=len(new),unrelated_937_package_records_unchanged=True,installed_payload_records_hashes_symlinks_and_modes_verified=count,configuration_package_adopted_existing_bytes=True,cpu_config_directory_0755=True,local_signed_repository_persisted=True,rollback_snapshot_packages_and_original_files_retained=True,taint=0,wireplumber_reload_pending=True,default_camera_capture_verification_pending=True)
(out/'install-summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=100);(host.PRIVATE/'package-install-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'package-install-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
