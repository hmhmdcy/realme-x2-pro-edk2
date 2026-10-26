from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import hashlib,json,subprocess
base=Path('/var/lib/samurai/k214-baseline');root=Path('/var/lib/samurai');out=root/'k214-package-transaction';stage=root/'k214-package-candidates'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(base/'boot-id-private.txt').read_bytes()
assert json.loads((out/'transaction-state-private.json').read_text())['state']=='verified'
db=Path('/lib/apk/db/installed').read_bytes();world=Path('/etc/apk/world').read_bytes()
manifest=json.loads((stage/'rollback-manifest-private.json').read_text())
for item in manifest['packages']:
    path=stage/'rollback'/item['file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']
    p=subprocess.run(['apk','verify',str(path)],capture_output=True,timeout=20);assert p.returncode==0
p=subprocess.run(['apk','--no-network','del','--simulate','samurai-camera-stack'],capture_output=True,text=True,timeout=30)
(out/'installed-rollback-remove-dry-private.log').write_text(p.stdout+p.stderr);assert p.returncode==0
actions=[line for line in p.stdout.splitlines() if line.startswith('(')];assert len(actions)==4
for name in ['samurai-camera-stack','samurai-camera-config','libcamera-v4l2','libcamera-gstreamer']:assert any(('Purging '+name+' (') in line for line in actions)
original=json.loads((base/'original-files-manifest-private.json').read_text())
for name,item in original.items():
    if item['kind']=='file':assert hashlib.sha256((base/'files'/name).read_bytes()).hexdigest()==item['sha256']
assert Path('/lib/apk/db/installed').read_bytes()==db and Path('/etc/apk/world').read_bytes()==world
(out/'installed-after-private.txt').write_bytes(db);(out/'world-after-private.txt').write_bytes(world)
report=dict(stage=214,current_native_rollback_remove_dry_run_passed=True,only_four_new_packages_would_be_removed=True,three_signed_installed_r4_snapshot_apks_verified_again=True,all_original_backup_bytes_intact=True,current_native_database_and_world_saved=True,actual_host_roundtrip_already_verified=True,configuration_and_world_must_be_restored_after_downgrade=True,real_rollback_not_sent=True)
(out/'rollback-ready-summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=80);(host.PRIVATE/'installed-rollback-ready-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'installed-rollback-readiness-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
