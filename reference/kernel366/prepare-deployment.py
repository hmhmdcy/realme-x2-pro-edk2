from pathlib import Path
import hashlib,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;OLD=HERE.parent/'kernel365'
build=json.loads((HERE/'build-package-validation.json').read_text());assert build['firmware_only_dtb_changed'] and build['all_firmware_code_and_non_version_data_unchanged']
assert json.loads((P/'firmware-output-restoration-private.json').read_text())['all_three_generated_outputs_restored']
guard=json.loads((P.parent/'kernel365/postboot-adoption-private.json').read_text())['guard_path']
for name in ['native-quiesce.py','restart-bootloader.py','run-transition-step.py','check-transition.py']:
 s=(OLD/name).read_text().replace('k365','k366').replace('stage=365','stage=366')
 s=s.replace('/var/lib/samurai/k363-work/boot-id-private.txt',guard)
 if name=='check-transition.py':s=s.replace("HERE.parent/'kernel363/boot-package-validation.json'","HERE.parent/'kernel365/boot-package-validation.json'")
 (HERE/name).write_text(s);compile(s,name,'exec')
s=(HERE.parent/'kernel276/flash-boot.py').read_text().replace('stage=276','stage=366').replace("['kernel_build']==183","['kernel_build']==363").replace('boot275_rollback','boot276_rollback')
(HERE/'flash-boot.py').write_text(s)
files={}
for key,path in [('boot_candidate',P/'boot-partition-k366-icp-dt.img'),('boot276_rollback',P.parent/'kernel276/boot-partition-k276-cci-io.img')]:
 files[key]=dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
assert files['boot_candidate']['sha256']==build['boot_sha256'] and files['boot276_rollback']['sha256']==build['rollback_boot_sha256']
(P/'deployment-lock-private.json').write_text(json.dumps(dict(files=files),indent=2)+'\n')
s=(OLD/'adopt-postboot.py').read_text().replace('k365','k366').replace('stage=365','stage=366')
s=s.replace("['logdump_flash_success']","['boot_flash_success']")
s=s.replace("package=json.loads((HERE/'boot-package-validation.json').read_text());dt=json.loads((HERE/'dt-build-validation.json').read_text())", "package=json.loads((HERE.parent/'kernel365/boot-package-validation.json').read_text());dt=json.loads((HERE.parent/'kernel365/dt-build-validation.json').read_text());package['firmware_boot_preserved_sha256']=json.loads((HERE/'build-package-validation.json').read_text())['boot_sha256']")
s=s.replace('effective=icp.exists()','effective=icp.exists();assert effective')
s=s.replace('firmware_preserved=True','firmware_update_readback_exact=True,firmware_boot_stage=366')
s=s.replace('logdump_dt_stage=366,effective_dt_stage=366','logdump_dt_stage=365,effective_dt_stage=365')
(HERE/'adopt-postboot.py').write_text(s)
for name in ['camera-check.py','camera-check-body.py']:
 s=(OLD/name).read_text().replace('k365','k366').replace('stage=365','stage=366').replace("'stage':365","'stage':366")
 s=s.replace('dt_stage=366','dt_stage=365')
 (HERE/name).write_text(s)
for name in ['flash-boot.py','adopt-postboot.py','camera-check.py','camera-check-body.py']:compile((HERE/name).read_text(),name,'exec')
print('Prepared boot-only EDK2 DT update; k363 Image/modules and logdump365 preserved.')
