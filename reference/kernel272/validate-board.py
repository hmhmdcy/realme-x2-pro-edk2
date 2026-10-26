"""Check the new static board against deployed DT270 and focused schemas."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel272')
W=Path('/home/cy122/x2pro-linux/camera270-kernel');B=Path('/home/cy122/x2pro-linux/camera272-build-r1')
pp=P/'main.pp.dts';yaml=P/'main.yaml';dtb=B/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'
q=subprocess.run(['cpp','-nostdinc','-undef','-D__DTS__','-x','assembler-with-cpp','-I',str(W/'scripts/dtc/include-prefixes'),str(W/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'),'-o',str(pp)],capture_output=True);assert q.returncode==0
q=subprocess.run(['dtc','-I','dts','-O','yaml','-o',str(yaml),str(pp)],capture_output=True)
(P/'main-dtc-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
spec=importlib.util.spec_from_file_location('fdt',R.parent/'kernel211/fdt_compare.py');f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
parse=f.parser()
old=parse(Path('/home/cy122/x2pro-linux/camera270-build-r1/arch/arm64/boot/dts/qcom/sm8150-samurai.dtb').read_bytes());new=parse(dtb.read_bytes())
delta=f.compare(old,new,yaml);(P/'main-dtb-semantic-private.json').write_text(json.dumps(delta,indent=2)+'\n')
assert not delta['only_old_nodes']
main=next(n for n,p in new.items() if p.get('compatible')==b'samsung,s5kgw1\0')
q=next(n for n,p in new.items() if n.endswith('/pmic@4') and p.get('qcom,initial-address'))
reset=next(n for n in new if n.endswith('/camera-main-reset-state'))
cci=main.rsplit('/',1)[0]
allowed={main,main+'/port',main+'/port/endpoint',q+'/regulators/ldo1',q+'/regulators/ldo3',q+'/regulators/ldo7',
 reset,'/soc@0/pinctrl@3100000/camera-main-mclk-active-state','/soc@0/pinctrl@3100000/camera-main-mclk-sleep-state',
 '/soc@0/camss@acb3000/ports/port@0','/soc@0/camss@acb3000/ports/port@0/endpoint'}
assert set(delta['only_new_nodes'])==allowed,(set(delta['only_new_nodes'])-allowed,allowed-set(delta['only_new_nodes']))
changed={(r['path'],r['property']) for r in delta['remaining_changed_properties']}
assert changed<={(cci,'status')},changed
checks={}
for select in ['samsung,s5kgw1','qcom,sm8150-camss','qcom,pm8008','qcom,pmic-gpio','reserved-memory']:
 cmd=['/home/cy122/x2pro-linux/.venv-dtschema/bin/dt-validate','-s',str(P/'schema272.json'),'-l',select,str(dtb)]
 out=subprocess.run(cmd,capture_output=True)
 (P/('main-schema-'+select.replace(',','-')+'-private.log')).write_bytes(out.stdout+out.stderr)
 checks[select]=dict(exit=out.returncode,diagnostic_bytes=len(out.stdout+out.stderr))
 assert out.returncode==0 and not out.stdout and not out.stderr,(select,'inspect private schema log')
report=dict(stage=272,dtb_sha256=hashlib.sha256(dtb.read_bytes()).hexdigest(),
 new_nodes=len(allowed),no_existing_nodes_removed=True,existing_property_changes=[list(v) for v in sorted(changed)],
 schema_validations=checks,existing_camera_and_other_peripheral_properties_preserved=True,
 static_sensor_and_standard_regulator_nodes=True,main_address7=16,hardware_not_yet_probed=True,phone_unchanged=True)
(R/'board-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
