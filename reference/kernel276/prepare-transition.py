from pathlib import Path
import base64,hashlib,json
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((R/'rollback-validation.json').read_text())['phone_and_pc_rollback_verified']
build=json.loads((R/'build-package-validation.json').read_text());files=dict(boot_candidate=dict(path=str(P/'boot-partition-k276-cci-io.img'),sha256=build['boot_sha256']),boot275_rollback=dict(path=str(P.parent/'kernel275/boot-partition-k275-main-lens.img'),sha256=build['rollback_boot_sha256']))
for row in files.values():assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256']
texts={}
for name in ['native-quiesce.py','restart-bootloader.py','launch-quiesce.py','poll-quiesce.py','submit-restart.py','flash-boot.py']:
 source=(R.parent/'kernel275'/name).read_text().replace('k275-work','__CURRENT_WORK__').replace('k275','k276').replace('stage=275','stage=276').replace('__CURRENT_WORK__','k275-work').replace('k273-work','k275-work').replace('k276-main-transaction','k276-cci-transaction-r2').replace('boot273_rollback','boot275_rollback')
 if name=='restart-bootloader.py':source=source.replace('packages-state-private.json','state-private.json')
 compile(source,name,'exec');p=R/name;assert not p.exists();p.write_text(source);texts[name]=source
args={name:base64.b64encode(texts[name].encode()).decode() for name in ['native-quiesce.py','restart-bootloader.py']}
code=r'''
from pathlib import Path
import base64,json,os
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k275-work/boot-id-private.txt').read_bytes()
assert json.loads((r/'k276-cci-transaction-r2/state-private.json').read_text())['exit_code']==0
assert not (r/'k276-quiesce').exists();os.umask(0o077);tools=r/'k276-tools';tools.mkdir(mode=0o700)
for name,data in args.items():p=tools/name;assert not p.exists();p.write_bytes(base64.b64decode(data));compile(p.read_bytes(),name,'exec')
print(json.dumps(dict(stage=276,current_boot275_verified=True,tools_prepared=True,no_services_stopped=True)))
'''
q=host.ssh('python3 -',input=('args='+repr(args)+'\n'+code).encode(),timeout=20);(P/'transition-prepare-private.json').write_bytes(q.stdout)
(P/'deployment-lock-private.json').write_text(json.dumps(dict(stage=276,files=files,rollback_archive_sha256=json.loads((R/'rollback-validation.json').read_text())['sha256']),indent=2)+'\n');print(q.stdout.decode())
for name in ['refresh-usb-endpoint.ps1','bootstrap-postboot.py','check-postboot.py']:
 source=(R.parent/'kernel275'/name).read_text().replace('kernel275','kernel276').replace('k275','k276').replace('stage=275','stage=276').replace('k273-work','k275-work').replace('K275_','K276_').replace('k276-main-transaction','k276-cci-transaction-r2')
 if name=='bootstrap-postboot.py':source=source.replace('packages-state-private.json','state-private.json')
 if name=='check-postboot.py':
  old="'s5kgw1','lc898219xi']";assert old in source;source=source.replace(old,"'s5kgw1','lc898219xi','i2c_qcom_cci']")
 if name.endswith('.py'):compile(source,name,'exec')
 p=R/name;assert not p.exists();p.write_text(source)
