"""Prepare this boot's guarded quiesce, package, reboot and DT-only flash sequence."""
from pathlib import Path
import base64,hashlib,json
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((R/'rollback-validation.json').read_text())['phone_and_pc_rollback_verified']
build=json.loads((R/'build-package-validation.json').read_text());assert build['firmware_only_dtb_changed'] and build['all_firmware_code_and_non_version_data_unchanged']
files=dict(boot_candidate=dict(path=str(P/'boot-partition-k275-main-lens.img'),sha256=build['boot_sha256']),boot273_rollback=dict(path=str(P.parent/'kernel273/boot-partition-k273-main-camera.img'),sha256=build['rollback_boot_sha256']))
for row in files.values():assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256']
texts={}
for name in ['native-quiesce.py','restart-bootloader.py','launch-quiesce.py','poll-quiesce.py','submit-restart.py','flash-boot.py','install-packages-quiesced.py']:
 text=(R.parent/'kernel273'/name).read_text().replace('k273','k275').replace('stage=273','stage=275').replace('k270-work','k273-work').replace('boot270_rollback','boot273_rollback')
 if name=='native-quiesce.py':
  old="['cam-front-vana','cam-front-vdig','cam-rear-vana','cam-rear-vdig','cam-tele-vana','cam-tele-vdig']"
  assert text.count(old)==1;text=text.replace(old,old[:-1]+",'cam-main-vana','cam-main-vdig','cam-main-vaf']")
 if name=='restart-bootloader.py':text=text.replace('packages-verified-state-private.json','packages-state-private.json')
 if name=='install-packages-quiesced.py':
  for a,b in [('len(now)==775','len(now)==776'),("Path('/sys/module/s5kgw1')","Path('/sys/module/lc898219xi')"),('samurai-camera-stack=0.1.0-r16','samurai-camera-stack=0.1.0-r17'),("framework_version='99990.7.2-r21'","framework_version='99990.7.2-r22'"),("config_version='0.1.0-r16'","config_version='0.1.0-r17'")]:assert a in text,a;text=text.replace(a,b)
 compile(text,name,'exec');assert not (R/name).exists();(R/name).write_text(text);texts[name]=text
code=r'''
from pathlib import Path
import base64,json,os
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k273-work/boot-id-private.txt').read_bytes()
assert json.loads((r/'k275-main-transaction/state-private.json').read_text())['exit_code']==0
assert not (r/'k275-quiesce').exists();os.umask(0o077);tools=r/'k275-tools';tools.mkdir(mode=0o700)
for name,data in args.items():
 p=tools/name;assert name in ['native-quiesce.py','restart-bootloader.py'] and not p.exists();p.write_bytes(base64.b64decode(data));compile(p.read_bytes(),name,'exec')
print(json.dumps(dict(tools_prepared=True,current_boot273_guard_verified=True,no_services_stopped=True)))
'''
args={name:base64.b64encode(texts[name].encode()).decode() for name in ['native-quiesce.py','restart-bootloader.py']}
q=host.ssh('python3 -',input=('args='+repr(args)+'\n'+code).encode(),timeout=20);(P/'transition-prepare-private.json').write_bytes(q.stdout)
(P/'deployment-lock-private.json').write_text(json.dumps(dict(stage=275,files=files,rollback_archive_sha256=json.loads((R/'rollback-validation.json').read_text())['sha256']),indent=2)+'\n');print(q.stdout.decode())
