"""Persist the front-camera config and build modules for deployed Image183."""
from pathlib import Path
import difflib,hashlib,json,os,shutil,subprocess,sys
os.umask(0o077)
here=Path(__file__).resolve().parent;k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
private=Path('/mnt/e/edk2-samurai-out/kernel210');out=private/'modules';resume='--continue-after-config-review' in sys.argv;out.mkdir(mode=0o700,exist_ok=resume)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert json.loads((here/'camera-dtb-validation.json').read_text())['only_intended_camera_nodes_and_cci_enable_vio_phandle_changed']
baseline=private/'source-before'
for name in (['Module.symvers','modules.order'] if resume else ['.config','Module.symvers','modules.order']):
    assert (k/name).read_bytes()==(baseline/name).read_bytes()
original_config=(baseline/'.config').read_text();base_symbols=(k/'Module.symvers').read_text();base_order=(k/'modules.order').read_text()
assert len(base_symbols.splitlines())==16793 and len(base_order.splitlines())==770
preserve={n:sha(k/n) for n in ['arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','drivers/media/i2c/imx471.c','drivers/mfd/qcom-pm8008.c','drivers/i2c/busses/i2c-qcom-cci.c']}
targets=['drivers/media/v4l2-core/v4l2-cci.ko','drivers/media/i2c/imx471.ko','drivers/mfd/qcom-pm8008.ko']
for n in targets:
    if (k/n).exists():
        backup=out/(Path(n).name+'.before-private')
        if backup.exists():assert sha(backup)==sha(k/n)
        else:shutil.copyfile(k/n,backup)
env=dict(os.environ,KBUILD_BUILD_VERSION='183',PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup')
if not resume:
    subprocess.run(['scripts/config','--module','VIDEO_IMX471'],cwd=k,check=True,capture_output=True)
    with (out/'olddefconfig-private.log').open('xb') as log:
        subprocess.run(['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','olddefconfig'],cwd=k,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
config=(k/'.config').read_text()
delta=set(config.splitlines())^set(original_config.splitlines())
expected={'# CONFIG_VIDEO_IMX471 is not set','CONFIG_VIDEO_IMX471=m','CONFIG_V4L2_CCI=m','CONFIG_V4L2_CCI_I2C=m'}|{'# CONFIG_OF_SAMURAI_'+n+' is not set' for n in ['CCI_BRINGUP','FRONT_IDENTIFY','PMIC_FIXTURE','FRONT_OVERLAY','VIO_PHANDLE']}
assert delta==expected,delta
(out/'config-diff-private.patch').write_text(''.join(difflib.unified_diff(original_config.splitlines(True),config.splitlines(True),fromfile='before.config',tofile='camera.config')))
(out/'config-camera-private').write_text(config)
with (out/'build-private.log').open('xb') as log:
    subprocess.run(['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LD=aarch64-linux-gnu-ld --no-keep-memory','W=1','-j3',*targets],cwd=k,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
(out/'generated-Module.symvers-private').write_bytes((k/'Module.symvers').read_bytes())
if (k/'modules.order').exists():(out/'generated-modules.order-private').write_bytes((k/'modules.order').read_bytes())
# A partial target build may write only its target exports. Preserve the Image183
# export inventory and add only the new CCI library's actual modpost exports.
generated=(k/'Module.symvers').read_text().splitlines()
allowed={n[:-3] for n in targets}
target_symbols=[l for l in generated if l.split()[2] in allowed]
assert any(l.split()[2]=='drivers/media/v4l2-core/v4l2-cci' for l in target_symbols)
combined={l.split()[1]:l for l in base_symbols.splitlines()}
added=[]
for line in target_symbols:
    name=line.split()[1]
    if name in combined:assert line==combined[name]
    else:combined[name]=line;added.append(name)
available=set(combined)
report_modules=[]
expected_vm=json.loads((here.parent/'kernel195/pmic-module-build-validation.json').read_text())['vermagic']
for name in targets:
    dest=out/Path(name).name;shutil.copyfile(k/name,dest)
    subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(dest)],check=True)
    imports=subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(dest)],text=True)
    assert all(l.split()[-1] in available for l in imports.splitlines() if l.strip())
    vm=subprocess.check_output(['modinfo','-F','vermagic',str(dest)],text=True).strip();assert vm==expected_vm
    assert subprocess.check_output(['modinfo','-F','intree',str(dest)],text=True).strip()=='Y'
    report_modules.append(dict(path=name,sha256=sha(dest),bytes=dest.stat().st_size,vermagic=vm,depends=subprocess.check_output(['modinfo','-F','depends',str(dest)],text=True).strip()))
diagnostics=[l for l in (out/'build-private.log').read_text().splitlines() if 'warning:' in l.lower() or 'error:' in l.lower()];assert not diagnostics,diagnostics
assert {n:sha(k/n) for n in preserve}==preserve
order=base_order.splitlines()
for n in targets:
    entry=n[:-3]+'.o'
    if entry not in order:order.append(entry)
assert len(order)==772 and len(set(order))==772
(k/'Module.symvers').write_text('\n'.join(combined.values())+'\n')
(k/'modules.order').write_text('\n'.join(order)+'\n')
assert (k/'.config').read_text()==config
report=dict(stage=210,persistent_camera_config_enabled=True,config_sha256=sha(k/'.config'),config_delta_lines=sorted(delta),modules=report_modules,w1_diagnostics=0,all_import_names_available=True,base_image_dtb_driver_sources_preserved=True,base_exports_preserved=True,new_cci_exports=len(added),combined_symbol_count=len(combined),modules_order_count=len(order),partial_build_metadata_merged_with_preserved_base=True,running_image_still183=True,full_kernel_rebuild=False,device_installed=False)
(here/'camera-module-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
plan=json.loads((private/'current-work-private.json').read_text());plan.update(state='210 static camera DTB validated; persistent .config enables IMX471/CCI, three W1 modules built with deployed183 vermagic/import inventory. No device install or transition yet.',next='Back up installed modules, check depmod dry-run, prepare boot package with only intended DTB changes; install three modules preserving all other files, then guarded boot transition.')
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps(report))
