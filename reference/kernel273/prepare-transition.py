"""Adapt the verified Image183 transition to fresh boot270 identities and r21."""
from pathlib import Path
import base64,hashlib,json,shlex
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((R/'rollback-validation.json').read_text())['phone_and_pc_rollback_verified']
proof=json.loads((R/'build-package-validation.json').read_text());assert proof['firmware_only_dtb_changed'] and proof['all_firmware_code_and_non_version_data_unchanged']
files=dict(boot_candidate=dict(path=str(P/'boot-partition-k273-main-camera.img'),sha256=proof['boot_sha256']),
 boot270_rollback=dict(path=str(P.parent/'kernel270/boot-partition-k270-telephoto.img'),sha256=proof['rollback_boot_sha256']))
for row in files.values():assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256']
quiesce=(R.parent/'kernel270/native-quiesce.py').read_text().replace('k270','k273').replace('stage=270','stage=273').replace('k269-work','k270-work').replace('k273-module-transaction','k273-main-transaction')
old="['cam-front-vana','cam-front-vdig','cam-back-vana','cam-back-vdig','cam-rear-vana','cam-rear-vdig']"
assert quiesce.count(old)==1;quiesce=quiesce.replace(old,"['cam-front-vana','cam-front-vdig','cam-rear-vana','cam-rear-vdig','cam-tele-vana','cam-tele-vdig']")
restart=(R.parent/'kernel270/restart-bootloader.py').read_text().replace('k270','k273').replace('stage=270','stage=273').replace('k269-work','k270-work')
needle="s=json.loads((r/'k273-quiesce/state-private.json').read_text())"
assert restart.count(needle)==1
restart=restart.replace(needle,"assert json.loads((r/'k273-main-transaction/packages-state-private.json').read_text())['exit_code']==0\n"+needle)
for name,text in [('native-quiesce.py',quiesce),('restart-bootloader.py',restart)]:
 compile(text,name,'exec');assert not (R/name).exists();(R/name).write_text(text)
for name in ['launch-quiesce.py','poll-quiesce.py','submit-restart.py','flash-boot.py']:
 text=(R.parent/'kernel270'/name).read_text().replace('k270','k273').replace('stage=270','stage=273').replace('k269-work','k270-work').replace('boot267_rollback','boot270_rollback')
 if name=='launch-quiesce.py':text=text.replace("['pc_and_phone_module_rollback_verified']","['phone_and_pc_rollback_verified']")
 compile(text,name,'exec');assert not (R/name).exists();(R/name).write_text(text)
sources={name:base64.b64encode(text.encode()).decode() for name,text in [('native-quiesce.py',quiesce),('restart-bootloader.py',restart)]}
code=r'''
from pathlib import Path
import base64,json,os
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k270-work/boot-id-private.txt').read_bytes()
assert json.loads((r/'k273-main-transaction/state-private.json').read_text())['exit_code']==0
assert not (r/'k273-quiesce').exists();os.umask(0o077);tools=r/'k273-tools';tools.mkdir(mode=0o700)
for name,data in args.items():
 p=tools/name;assert name in ['native-quiesce.py','restart-bootloader.py'] and not p.exists();p.write_bytes(base64.b64decode(data));compile(p.read_bytes(),name,'exec')
print(json.dumps(dict(tools_prepared=True,current_boot_guard_verified=True,no_services_stopped=True)))
'''
q=host.ssh('python3 -',input=('args='+repr(sources)+'\n'+code).encode(),timeout=20)
(P/'transition-prepare-private.json').write_bytes(q.stdout)
(P/'deployment-lock-private.json').write_text(json.dumps(dict(stage=273,files=files,rollback_archive_sha256=json.loads((R/'rollback-validation.json').read_text())['sha256']),indent=2)+'\n')
print(q.stdout.decode())
