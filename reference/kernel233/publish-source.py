"""Publish the accepted experimental component without altering the frozen kernel."""
from pathlib import Path
import hashlib,importlib.util,json,shutil
R=Path(__file__).resolve().parent;ROOT=R.parents[1];P=Path('/mnt/e/edk2-samurai-out/kernel233')
out=ROOT/'linux-port/camera/pmic';out.mkdir(exist_ok=True)
names=['qcom-pm8008.c','reset-realme-rmx1931-pm8008.c','pm8008-reset-backend-dependency.patch',
 'Kconfig.fragment','Makefile.fragment','experimental-p-identity-only.dts','product-p-disabled.dts']
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
for name in names:shutil.copyfile(R.parent/'kernel232'/name,out/name)
host=json.loads((R.parent/'kernel232/host-tests-validation.json').read_text())
assert sha(out/'qcom-pm8008.c')==host['mfd_sha256'] and sha(out/'reset-realme-rmx1931-pm8008.c')==host['provider_sha256']
runtime=json.loads((R/'runtime-validation.json').read_text());health=json.loads((R/'final-health-validation.json').read_text());cycles=json.loads((R/'pmic-cycles-validation.json').read_text())
assert runtime['new_pmic_modules_loaded_notes_match'] and runtime['p_identity_read_verified']
assert health['taint']==0 and not any(health['fault_counts'].values()) and cycles['provider_cold_cycle']['one_cold_address_assignment']
sp=importlib.util.spec_from_file_location('p227',R.parent/'kernel227/prepare-fastrpc.py');p=importlib.util.module_from_spec(sp);sp.loader.exec_module(p)
assert p.snapshot()==json.loads((P.parent/'kernel228/canonical-after-private.json').read_text())
boot=json.loads((R.parent/'kernel232/build-package-validation.json').read_text())
lock=dict(stage=233,profile='experimental P identity-only; rear capture incomplete',source_files={n:sha(out/n) for n in names},
 modules=json.loads((R.parent/'kernel232/module-build-validation.json').read_text())['modules'],
 dtb_sha256=boot['dtb_sha256'],boot_sha256=boot['boot_sha256'],rollback_boot_sha256=boot['rollback_boot_sha256'],
 kernel_image_sha256=boot['kernel_image_preserved'],logdump_sha256=boot['logdump_preserved'],
 mfd_pre233_sha256='d1ff82c022577e65b8d5cf8d98e56ea4170eb5bf4138516be843736db25a9dea',
 modules_must_match_compiled_dt=True,preload_options=['experimental_p_address_only=1'],softdep_provider='reset_realme_rmx1931_pm8008',
 native_loaded_notes_verified=True,native_p_identity_no_children=True,q_warm_and_provider_cold_cycles=True,
 front_raw_rgb_six_frames_each=True,taint=0,full_vin_schema_and_rear_capture_complete=False,canonical_after228_preserved=True)
(out/'source-lock.json').write_text(json.dumps(lock,indent=2)+'\n')
print(json.dumps(dict(stage=233,accepted_component_sources_published=len(names),canonical_after228_preserved=True)))
