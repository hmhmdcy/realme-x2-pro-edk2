"""Validate binding constraints without inventing physical PMIC input nets."""
from pathlib import Path
import copy,json,subprocess
import dtschema
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel194');bin=Path('/home/cy122/x2pro-linux/schema-k194/venv/bin');schema=k/'Documentation/devicetree/bindings/mfd/qcom,pm8008.yaml';processed=out/'processed-pmic-private.json'
for name,args in [('doc',[str(bin/'dt-doc-validate'),'-u',str(k/'Documentation/devicetree/bindings'),str(schema)]),('compile',[str(bin/'dt-mk-schema'),'-j','-o',str(processed),str(schema),str(k/'Documentation/devicetree/bindings/regulator/regulator.yaml')])]:
 p=subprocess.run(args,capture_output=True,timeout=90);(out/('pmic-schema-'+name+'-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0 and not p.stdout and not p.stderr,(name,(p.stdout+p.stderr).decode()[-2200:])
v=dtschema.DTValidator([str(processed)]);node=v.decode_dtb((out/'sm8150-samurai-camera-warm-private.dtb').read_bytes())[0]
for part in ['soc@0','geniqup@8c0000','i2c@890000','pmic@4']:node=node[part]
node['$nodename']=['pmic@4']
def errors(n):return list(v.iter_errors(n,filter=['qcom,pm8008']))
actual=errors(node);assert len(actual)==4 and all('required property' in e.message and any(n in e.message for n in ['vdd-l3-l4','vdd-l5','vdd-l6','vdd-l7']) for e in actual),[e.message for e in actual]
# Synthetic schema-only fixture: equal numeric phandles here are NOT wiring evidence.
fixture=copy.deepcopy(node)
for p in ['vdd-l3-l4-supply','vdd-l5-supply','vdd-l6-supply','vdd-l7-supply']:fixture[p]=copy.deepcopy(fixture['vdd-l1-l2-supply'])
assert not errors(fixture),[e.message for e in errors(fixture)]
tests=[]
for name in ['missing-reset','wrong-initial','wrong-assigned','legacy-no-migration']:
 n=copy.deepcopy(fixture)
 if name=='missing-reset':del n['reset-gpios']
 if name=='wrong-initial':n['qcom,initial-address']=[9]
 if name in ['wrong-assigned','legacy-no-migration']:n['reg']=[[8]]
 if name=='legacy-no-migration':del n['qcom,initial-address']
 e=errors(n);valid=name=='legacy-no-migration';assert bool(e)!=valid,(name,[x.message for x in e]);tests.append(dict(name=name,expected_valid=valid,error_count=len(e)))
r=dict(stage=194,dtschema_version=dtschema.__version__,doc_and_schema_compile_clean=True,synthetic_complete_fixture_valid=True,synthetic_fixture_is_not_physical_wiring=True,controls=tests,actual_partial_candidate_missing_four_pldo_inputs=True,actual_partial_candidate_error_count=len(actual),full_board_binding_valid=False)
(ref/'pmic-schema-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
