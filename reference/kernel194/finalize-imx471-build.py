"""Package the already completed build; V4L2's I2C backend is in v4l2-cci.ko."""
from pathlib import Path
import hashlib,json,subprocess,shutil
ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel194');k=Path('/home/cy122/pmos-samurai-kernel136/kernel');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=json.loads((ref/'imx471-source-validation.json').read_text());assert sha(k/'drivers/media/i2c/imx471.c')==source['source_sha256']
assert all(sha(k/n)==h for n,h in source['prior16_tracked_sources'].items())
base=json.loads((ref.parent/'kernel183/build-package-validation.json').read_text());assert sha(k/'arch/arm64/boot/Image')==base['image_sha256'] and sha(k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb')==base['dtb_sha256']
for name in ['.config','Module.symvers','modules.order']:assert (k/name).read_bytes()==(out/('original-'+name.replace('.','_')+'-private')).read_bytes()
symbols=(out/'new-module-symbols-private').read_text();available={s.split()[1] for s in symbols.splitlines()};records=[]
for name in ['drivers/media/v4l2-core/v4l2-cci.ko','drivers/media/i2c/imx471.ko']:
 p=k/name;temporary=out/(p.name+'.verify-private');shutil.copyfile(p,temporary);subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(temporary)],check=True);dest=out/p.name
 if dest.exists():assert sha(dest)==sha(temporary)
 else:shutil.copyfile(temporary,dest)
 vm=subprocess.check_output(['modinfo','-F','vermagic',str(dest)],text=True).strip();assert vm==subprocess.check_output(['modinfo','-F','vermagic',str(k/'drivers/misc/fastrpc.ko')],text=True).strip()
 imports=subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(dest)],text=True);assert all(line.split()[-1] in available for line in imports.splitlines() if line.strip())
 assert subprocess.check_output(['modinfo','-F','intree',str(dest)],text=True).strip()=='Y'
 records.append(dict(path=name,sha256=sha(dest),bytes=dest.stat().st_size,vermagic=vm,depends=subprocess.check_output(['modinfo','-F','depends',str(dest)],text=True).strip()))
log=(out/'imx471-modules-build-private.log').read_text();diagnostics=[s for s in log.splitlines() if 'warning:' in s or 'error:' in s];assert len(diagnostics)==5 and not any('error:' in s or 'imx471' in s or 'v4l2-cci' in s for s in diagnostics)
(out/'imx471-build-diagnostics-private.json').write_text(json.dumps(diagnostics,indent=2)+'\n')
report=dict(stage=194,source_sha256=source['source_sha256'],modules=records,i2c_backend_is_part_of_cci_module=True,full_modules_build_completed=True,all_imports_checked_against_combined_symbols=True,image_dtb_config_unchanged=True,prior16_tracked_sources_unchanged=True,full_symbol_table_and_order_restored=True,target_w1_diagnostics=0,unrelated_full_tree_w1_warnings=5,first_packaging_missing_standalone_i2c_backend_corrected_without_rebuilding=True,hardware_deployed=False)
(ref/'imx471-modules-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
