"""Check only the changed binding/DT roles and retained matching providers."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tarfile

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('binding462_storage449',HERE.parent/'kernel449/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
SHARED=storage.mount.mounted_build();SOURCE=SHARED.parent/'kernel462-shared-camera-private/source-view'
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel462');tools=Path('/home/cy122/x2pro-linux/.venv-dtschema/bin')
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
load=lambda path:json.loads(Path(path).read_text())
assert shutil.disk_usage(SHARED).free>=2*1024**3
report_build=load(HERE/'target-build-r1-validation.json')
log=(PRIVATE/'target-build-r1-private.log').read_text()
report_build['diagnostics']=[line for line in log.splitlines() if re.search(r'warning(?:\s|\(|:)|error:',line,re.I)]
report_build['c_compiler_diagnostics']=[line for line in report_build['diagnostics'] if ': warning:' in line.lower() or ': error:' in line.lower()]
report_build['dtc_warnings']=[line for line in report_build['diagnostics'] if 'Warning (' in line]
report_build['diagnostic_classification_recomputed_from_original_log']=True
assert len(report_build['dtc_warnings'])==2 and not report_build['c_compiler_diagnostics']
(HERE/'target-build-r1-validation.json').write_text(json.dumps(report_build,indent=2)+'\n')

def run(name,args):
    proc=subprocess.run(args,capture_output=True)
    (PRIVATE/(name+'-private.log')).write_bytes(proc.stdout+proc.stderr)
    return dict(exit=proc.returncode,diagnostic_bytes=len(proc.stdout+proc.stderr))

binding=SOURCE/'Documentation/devicetree/bindings/media/i2c/sony,imx471.yaml'
doc=run('binding-doc',[str(tools/'dt-doc-validate'),str(binding)])
assert doc==dict(exit=0,diagnostic_bytes=0),doc
processed=PRIVATE/'schema462-private.json'
mk=run('binding-process',[str(tools/'dt-mk-schema'),'-j','-o',str(processed),str(SOURCE/'Documentation/devicetree/bindings')])
assert mk['exit']==0,mk
dtb=PRIVATE/'sm8150-samurai.dtb-r1'
validations={selector:run('binding-'+selector.replace(',','-'),[str(tools/'dt-validate'),'-s',str(processed),'-l',selector,str(dtb)])
             for selector in ['sony,imx471','gpio-mux','mux-controller']}
assert all(result==dict(exit=0,diagnostic_bytes=0) for result in validations.values()),validations
spec=importlib.util.spec_from_file_location('fdt462',HERE.parent/'kernel211/fdt_compare.py')
fdt=importlib.util.module_from_spec(spec);spec.loader.exec_module(fdt)
nodes=fdt.parser()(dtb.read_bytes())
muxes={name:row for name,row in nodes.items() if row.get('compatible')==b'gpio-mux\0'}
assert len(muxes)==1
muxname,mux=next(iter(muxes.items()))
fronts={name:row for name,row in nodes.items() if row.get('compatible')==b'sony,imx471\0'}
assert len(fronts)==1
frontname,front=next(iter(fronts.items()))
assert int.from_bytes(mux['#mux-state-cells'],'big')==1 and 'idle-state' not in mux
assert front['mux-states']==mux['phandle']+(1).to_bytes(4,'big') and front['mux-state-names']==b'csi-route\0'
assert not any(name.startswith('pinctrl-') or name.startswith('assigned-clock') for name in front)
assert front['reset-gpios'][-8:]==(12).to_bytes(4,'big')+(1).to_bytes(4,'big')
assert mux['mux-gpios'][-8:]==(29).to_bytes(4,'big')+bytes(4)
assert not any(b'ov02a1b' in row.get('compatible',b'') for row in nodes.values())

config=(PRIVATE.parent/'kernel457/config363-private').read_text()
assert all(line in config.splitlines() for line in ['CONFIG_MULTIPLEXER=y','CONFIG_MUX_GPIO=m','CONFIG_RESET_GPIO=m'])
package=load(HERE.parent/'kernel363/boot-package-validation.json')
archive=PRIVATE.parent/'kernel363/modules-k363-private.tar.gz'
assert sha(archive)==package['module_archive']['sha256']
inventory=load(PRIVATE.parent/'kernel363/installed-module-inventory-private.json')
root='usr/lib/modules/'+package['release']+'/'
providers=[]
symbols={line.split()[1] for line in (SHARED/'Module.symvers').read_text().splitlines()}
with tarfile.open(archive,'r:gz') as tar:
    for relative in ['kernel/drivers/mux/mux-gpio.ko','kernel/drivers/reset/reset-gpio.ko']:
        member=tar.getmember(root+relative);assert member.isfile()
        raw=tar.extractfile(member).read();assert hashlib.sha256(raw).hexdigest()==inventory[relative]
        path=PRIVATE/Path(relative).name;path.write_bytes(raw)
        get=lambda key:subprocess.check_output(['modinfo','-F',key,str(path)],text=True).strip()
        imports=sorted({line.split()[-1] for line in subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(path)],text=True).splitlines() if line.strip()})
        assert get('vermagic').split()[0]==package['release'] and get('intree')=='Y'
        assert set(imports)<=symbols,set(imports)-symbols
        providers.append(dict(path=relative,sha256=sha(path),bytes=len(raw),vermagic=get('vermagic'),intree=True,
                         alias=get('alias'),depends=get('depends'),import_count=len(imports),all_imports_in_image363=True))
post=load(HERE.parent/'kernel363/postboot-validation.json');assert post['all778_installed_modules_verified']
imx_object=PRIVATE/'imx471.o-r1'
imports=sorted({line.split()[-1] for line in subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(imx_object)],text=True).splitlines() if line.strip()})
module_metadata={'__this_module'}
assert set(imports)-module_metadata<=symbols,set(imports)-module_metadata-symbols
report=dict(stage=462,passed=True,doc=doc,processed_schema=mk,targeted_validations=validations,
    candidate_binding_sha256=sha(binding),dtb_sha256=sha(dtb),source_imx_object_imports_in_image363=True,
    object_imports=imports,front_has_no_automatic_shared_pins_or_assigned_clocks=True,
    object_module_metadata_resolved_by_future_mod_o=sorted(set(imports)&module_metadata),
    route_is_single_gpio_mux_state1=True,reset_gpio12_owned_via_reset_framework=True,fifth_node_absent=True,
    providers=providers,multiplexer_core_builtin_via_config_multiplexer=True,
    historical_postboot_all778_install_receipt=True,current_phone_files_or_loaded_providers_not_checked=True,
    fresh_modprobe_alias_provider_readiness_check_still_required=True,
    source354_or_existing_453_455_456_outputs_modified=False,phone_sdk_accessed=False,deployable=False)
(HERE/'binding-provider-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
