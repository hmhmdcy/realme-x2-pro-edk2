from pathlib import Path
import hashlib,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'module-install-validation.json').read_text())['passed']
guard='/var/lib/samurai/k378-recovered/boot-id-private.txt'
for name in ['native-quiesce.py','restart-bootloader.py','run-transition-step.py']:
 s=(HERE.parent/'kernel366'/name).read_text().replace('k366','k390').replace('stage=366','stage=390').replace('stage=366','stage=390')
 s=s.replace('/var/lib/samurai/k365-work/boot-id-private.txt',guard)
 s=s.replace("assert json.loads((r/'k363-deployment/module-install-validation-private.json').read_text())['all778_installed_hashes_verified']", "assert json.loads((r/'k390-deployment/state.json').read_text())['candidate_files_installed']")
 compile(s,name,'exec');(HERE/name).write_text(s)
boot=json.loads((HERE.parent/'kernel389/build-package-validation.json').read_text());(P/'build-package-validation.json').write_text(json.dumps(boot,indent=2)+'\n')
files={}
for key,path,digest in [('boot_candidate',P.parent/'kernel389/boot-partition-k389-icp-platform.img',boot['boot_sha256']),('boot366_rollback',P.parent/'kernel366/boot-partition-k366-icp-dt.img',boot['rollback_boot_sha256'])]:
 assert hashlib.sha256(path.read_bytes()).hexdigest()==digest;files[key]=dict(path=str(path),sha256=digest)
(P/'deployment-lock-private.json').write_text(json.dumps(dict(files=files),indent=2)+'\n')
s=(HERE.parent/'kernel366/flash-boot.py').read_text().replace('stage=366','stage=390').replace('boot276_rollback','boot366_rollback');compile(s,'flash-boot.py','exec');(HERE/'flash-boot.py').write_text(s)
print('Prepared390 transition with guard378, exact389 boot and boot366 rollback.')
