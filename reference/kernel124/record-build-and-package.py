from pathlib import Path
import runpy,subprocess,json,hashlib,shutil
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel124';out=Path('/mnt/e/edk2-samurai-out/kernel124');runpy.run_path(str(r/'reference/kernel122/ensure-rootfs-volume.py'))
v=Path('/home/cy122/pmos-samurai-rootfs122');k=v/'camera124/kernel'
subprocess.run(['git','diff','--check','--','drivers/media/platform/qcom/camss','arch/arm64/boot/dts/qcom/sm8150-samurai.dts'],cwd=k,check=True,timeout=90)
with (out/'patch-apply-dry-run-private.txt').open('w') as log:
 p=subprocess.run(['patch','--dry-run','-p1','-i',str(ref/'sm8150-cphy-power-7.3.patch')],cwd=v/'camera123/kernel',stdout=log,stderr=subprocess.STDOUT,timeout=30);assert p.returncode==0
assert 'error:' not in (out/'kernel-full-build.log').read_text().lower()
identity=subprocess.check_output(['strings',str(k/'vmlinux')],text=True);banners=[l for l in identity.splitlines() if l.startswith('Linux version 7.')];assert banners and all('#124 SMP' in l for l in banners)
artifacts=[]
for rel,label in [('arch/arm64/boot/Image','Image'),('arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','DTB'),('drivers/media/platform/qcom/camss/qcom-camss.ko','CAMSS')]:
 p=k/rel;data=p.read_bytes();assert data;(out/(label+'-k124-private')).write_bytes(data);artifacts.append(dict(artifact=label,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
report=dict(candidate=124,full_image_modules_dtb_build_pass=True,module_count=len(list(k.rglob('*.ko'))),artifacts=artifacts,matching_full_rootfs124_not_generated=True,not_deployed=True,patch_applies_cleanly_to_123=True,source_whitespace_check_pass=True,goal_complete=False)
assert report['module_count']==770;(ref/'kernel-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
code=(r/'reference/kernel123/verify-package.py').read_text().replace('123','124');(ref/'verify-package.py').write_text(code);exec(compile(code,'verify-package124','exec'),{})
code=(r/'reference/kernel123/compare-modules-and-health.py').read_text().replace('123','124').replace('a=modules(121);b=modules(124)','a=modules(123);b=modules(124)').replace('changed_vs121','changed_vs123');(ref/'compare-modules-and-health.py').write_text(code);exec(compile(code,'compare-modules-health124','exec'),{})
print('K124_BUILD_PACKAGE_SOURCE_AND_PHONE_HEALTH_VALIDATED')
