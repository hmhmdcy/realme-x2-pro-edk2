"""Package a DT-only update and prepare one current-boot guarded transition."""
from pathlib import Path
import hashlib,json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;OLD=HERE.parent/'kernel363'
dt=json.loads((HERE/'dt-build-validation.json').read_text());assert dt['passed'] and dt['icp_disabled']
old=json.loads((OLD/'boot-package-validation.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rollback=P.parent/'kernel363/logdump-k363-candidate-private.img';assert sha(rollback)==old['logdump_sha256']
target=P/'logdump-k365-candidate-private.img';assert not target.exists();shutil.copyfile(rollback,target)
newdt=P/'samurai365-private.dtb';assert sha(newdt)==dt['dtb_sha256']
subprocess.run(['mcopy','-o','-i',str(target),str(newdt),'::/samurai.dtb'],check=True)
assert subprocess.check_output(['mcopy','-i',str(target),'::/samurai.dtb','-'])==newdt.read_bytes()
assert hashlib.sha256(subprocess.check_output(['mcopy','-i',str(target),'::/Image','-'])).hexdigest()==old['image_sha256']
q=subprocess.run(['fsck.fat','-n',str(target)],capture_output=True);(P/'fat-check-private.log').write_bytes(q.stdout+q.stderr);q.check_returncode()
package=dict(old,stage=365,dt_commit=dt['commit'],kernel_build=363,kernel_image_stage=363,dt_stage=365,
    dtb_sha256=dt['dtb_sha256'],logdump_sha256=sha(target),rollback_logdump_sha256=old['logdump_sha256'],
    existing_kernel_image_and_modules_unchanged=True,static_icp_disabled=True,not_deployed=True)
(HERE/'boot-package-validation.json').write_text(json.dumps(package,indent=2)+'\n')
adopt=json.loads((P.parent/'kernel363/postboot-adoption-private.json').read_text())
for name in ['native-quiesce.py','restart-bootloader.py']:
 s=(OLD/name).read_text().replace('k363','k365').replace('stage=363','stage=365')
 s=s.replace('k365-deployment/module-install-validation-private.json','k363-deployment/module-install-validation-private.json')
 s=s.replace('/var/lib/samurai/k360-recovered/boot-id-private.txt',adopt['guard_path']).replace("startswith('#298 ')","startswith('#363 ')")
 (HERE/name).write_text(s);compile(s,name,'exec')
s=(OLD/'run-transition-step.py').read_text().replace('k363','k365').replace('stage=363','stage=365')
(HERE/'run-transition-step.py').write_text(s)
s=(OLD/'flash-logdump.py').read_text().replace('stage=363','stage=365')
(HERE/'flash-logdump.py').write_text(s)
files={}
for key,path in [('candidate',target),('rollback',rollback),('firmware',P.parent/'kernel276/boot-partition-k276-cci-io.img')]:
 files[key]=dict(path=str(path),bytes=path.stat().st_size,sha256=sha(path))
(P/'deployment-lock-private.json').write_text(json.dumps(dict(files=files),indent=2)+'\n')
print(json.dumps(dict(stage=365,dt_only=True,kernel_image_stage=363,logdump_sha256=package['logdump_sha256'],ready=True)))
