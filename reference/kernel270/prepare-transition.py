"""Prepare one guarded transition and collect its rollback before stopping services."""
from pathlib import Path
import base64,hashlib,json,shlex
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE
proof=json.loads((R/'build-package-validation.json').read_text())
assert json.loads((R/'module-stage-validation.json').read_text())['new_module_staged']
for field in ['firmware_only_dtb_changed','all_firmware_code_and_non_version_data_unchanged','bootshim_ramdisk_android_header_compat_preserved']:
 assert proof[field]
files=dict(boot_candidate=dict(path=str(P/'boot-partition-k270-telephoto.img'),sha256=proof['boot_sha256']),
 boot267_rollback=dict(path=str(P.parent/'kernel267/boot-partition-k267-common-camera.img'),sha256=proof['rollback_boot_sha256']))
for row in files.values():assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256']
quiesce=(R.parent/'kernel267/native-quiesce.py').read_text().replace('k267','k270').replace('stage=267','stage=270').replace('k260-work','k269-work').replace("['three_common_modules_staged']","['new_module_staged']")
restart=(R.parent/'kernel267/restart-bootloader.py').read_text().replace('k267','k270').replace('stage=267','stage=270').replace('k260-work','k269-work')
for name,text in [('native-quiesce.py',quiesce),('restart-bootloader.py',restart)]:compile(text,name,'exec');(R/name).write_text(text)
flash=(R.parent/'kernel267/flash-boot.py').read_text().replace('stage=267','stage=270').replace('boot235_rollback','boot267_rollback')
compile(flash,'flash-boot.py','exec');(R/'flash-boot.py').write_text(flash)
sources={name:base64.b64encode(text.encode()).decode() for name,text in [('native-quiesce.py',quiesce),('restart-bootloader.py',restart)]}
code=r'''
from pathlib import Path
import base64,hashlib,json,os,subprocess,sys
os.umask(0o077);args=json.load(sys.stdin);root=Path('/var/lib/samurai');tools=root/'k270-tools'
assert tools.is_dir() and not tools.is_symlink()
assert not (root/'k270-quiesce').exists()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k269-work/boot-id-private.txt').read_bytes()
assert json.loads((root/'k270-module-transaction/state-private.json').read_text())['exit_code']==0
for name,data in args.items():
 p=tools/name;assert name in ['native-quiesce.py','restart-bootloader.py'] and not p.exists()
 p.write_bytes(base64.b64decode(data));compile(p.read_bytes(),name,'exec')
archive=root/'k270-module-rollback-private.tar.gz';assert not archive.exists()
subprocess.run(['tar','-czf',str(archive),'-C',str(root),'k270-module-transaction'],capture_output=True,check=True)
print(json.dumps(dict(bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest())))
'''
q=host.ssh('python3 -c '+shlex.quote(code),input=json.dumps(sources).encode(),timeout=20);archive=json.loads(q.stdout)
pieces=[]
for offset in range(0,archive['bytes'],32768):
 fetch="from pathlib import Path;import sys;p=Path('/var/lib/samurai/k270-module-rollback-private.tar.gz');f=p.open('rb');f.seek("+str(offset)+");sys.stdout.buffer.write(f.read(32768))"
 q=host.ssh('python3 -c '+shlex.quote(fetch),timeout=20);assert len(q.stdout)==min(32768,archive['bytes']-offset);pieces.append(q.stdout)
payload=b''.join(pieces);assert len(payload)==archive['bytes'] and hashlib.sha256(payload).hexdigest()==archive['sha256']
(P/'module-rollback-private.tar.gz').write_bytes(payload)
lock=dict(stage=270,files=files,module_backup_sha256=archive['sha256'])
(P/'deployment-lock-private.json').write_text(json.dumps(lock,indent=2)+'\n')
report=dict(stage=270,pc_and_phone_module_rollback_verified=True,rollback_archive_bytes=len(payload),
 rollback_archive_sha256=archive['sha256'],current_boot267_and_candidate270_hashes_verified=True,
 fresh_guarded_transition_sources_prepared=True,no_services_stopped=True,no_restart_submitted=True)
(R/'rollback-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
