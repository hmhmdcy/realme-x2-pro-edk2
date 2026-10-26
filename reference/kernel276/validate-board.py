"""Require only the two board CCI supply connections to differ from deployed275."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE;W=Path('/home/cy122/x2pro-linux/camera270-kernel');B=Path('/home/cy122/x2pro-linux/camera276-build-r1');bin=Path('/home/cy122/x2pro-linux/.venv-dtschema/bin');dtb=B/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'
binding=W/'Documentation/devicetree/bindings/i2c/qcom,i2c-cci.yaml';q=subprocess.run([str(bin/'dt-doc-validate'),str(binding)],capture_output=True);(P/'cci-binding-doc-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0 and not q.stdout and not q.stderr
pp=P/'cci-board.pp.dts';yaml=P/'cci-board.yaml'
q=subprocess.run(['cpp','-nostdinc','-undef','-D__DTS__','-x','assembler-with-cpp','-I',str(W/'scripts/dtc/include-prefixes'),str(W/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'),'-o',str(pp)],capture_output=True);assert q.returncode==0
q=subprocess.run(['dtc','-I','dts','-O','yaml','-o',str(yaml),str(pp)],capture_output=True);(P/'cci-board-dtc-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
spec=importlib.util.spec_from_file_location('fdt276',R.parent/'kernel211/fdt_compare.py');f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f);parse=f.parser()
old=parse(Path('/home/cy122/x2pro-linux/camera274-build-r1/arch/arm64/boot/dts/qcom/sm8150-samurai.dtb').read_bytes());new=parse(dtb.read_bytes());delta=f.compare(old,new,yaml)
(P/'cci-board-semantic-private.json').write_text(json.dumps(delta,indent=2)+'\n')
assert not delta['only_old_nodes'] and not delta['only_new_nodes']
changes={(v['path'],v['property']) for v in delta['remaining_changed_properties']};assert changes=={('/soc@0/cci@ac4a000','vddio-supply'),('/soc@0/cci@ac4b000','vddio-supply')},changes
v=new['/soc@0/cci@ac4a000']['vddio-supply'];assert new['/soc@0/cci@ac4b000']['vddio-supply']==v==new['/soc@0/cci@ac4a000/i2c-bus@0/camera@10']['vddio-supply']
q=subprocess.run([str(bin/'dt-mk-schema'),'-j','-o',str(P/'schema276.json'),str(W/'Documentation/devicetree/bindings')],capture_output=True,timeout=90);(P/'cci-schema-build-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
checks={}
for select in ['qcom,i2c-cci','onnn,lc898219xi','samsung,s5kgw1']:
 q=subprocess.run([str(bin/'dt-validate'),'-s',str(P/'schema276.json'),'-l',select,str(dtb)],capture_output=True);(P/('cci-schema-'+select.replace(',','-')+'-private.log')).write_bytes(q.stdout+q.stderr);checks[select]=dict(exit=q.returncode,diagnostic_bytes=len(q.stdout+q.stderr));assert q.returncode==0 and not q.stdout and not q.stderr
d=dict(stage=276,dtb_sha256=hashlib.sha256(dtb.read_bytes()).hexdigest(),new_nodes=0,no_nodes_removed=True,existing_changed_properties=sorted([list(v) for v in changes]),shared_cci_io_supply_matches_sensor_io=True,no_soc_dtsi_change=True,schema_validations=checks,board_candidate_not_deployed=True)
(R/'board-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
