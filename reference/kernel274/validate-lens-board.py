"""Check lens graph and sole VAF ownership separately from SoC and sensor resources."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE;W=Path('/home/cy122/x2pro-linux/camera270-kernel');B=Path('/home/cy122/x2pro-linux/camera274-build-r1');bin=Path('/home/cy122/x2pro-linux/.venv-dtschema/bin')
pp=P/'lens-board.pp.dts';yaml=P/'lens-board.yaml';dtb=B/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'
q=subprocess.run(['cpp','-nostdinc','-undef','-D__DTS__','-x','assembler-with-cpp','-I',str(W/'scripts/dtc/include-prefixes'),str(W/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'),'-o',str(pp)],capture_output=True);assert q.returncode==0
q=subprocess.run(['dtc','-I','dts','-O','yaml','-o',str(yaml),str(pp)],capture_output=True);(P/'lens-board-dtc-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
spec=importlib.util.spec_from_file_location('fdt274',R.parent/'kernel211/fdt_compare.py');f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f);parse=f.parser()
old=parse(Path('/home/cy122/x2pro-linux/camera272-build-r1/arch/arm64/boot/dts/qcom/sm8150-samurai.dtb').read_bytes());new=parse(dtb.read_bytes())
delta=f.compare(old,new,yaml);(P/'lens-board-semantic-private.json').write_text(json.dumps(delta,indent=2)+'\n')
lens=next(n for n,p in new.items() if p.get('compatible')==b'onnn,lc898219xi\0');sensor=next(n for n,p in new.items() if p.get('compatible')==b'samsung,s5kgw1\0')
assert not delta['only_old_nodes'] and delta['only_new_nodes']==[lens]
changes={(v['path'],v['property']) for v in delta['remaining_changed_properties']};assert changes=={(sensor,'afvdd-supply'),(sensor,'lens-focus')},changes
assert new[sensor]['lens-focus']==new[lens]['phandle'] and 'afvdd-supply' not in new[sensor]
vaf=new[lens]['vdd-supply'];assert old[sensor]['afvdd-supply']==vaf or next(p for p,v in old.items() if v.get('phandle')==old[sensor]['afvdd-supply'])==next(p for p,v in new.items() if v.get('phandle')==vaf)
consumers=[(p,k) for p,props in new.items() for k,v in props.items() if k.endswith('-supply') and v==vaf];assert consumers==[(lens,'vdd-supply')],consumers
q=subprocess.run([str(bin/'dt-mk-schema'),'-j','-o',str(P/'schema274.json'),str(W/'Documentation/devicetree/bindings')],capture_output=True,timeout=90)
(P/'lens-schema-build-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
checks={}
for select in ['onnn,lc898219xi','samsung,s5kgw1','qcom,pm8008']:
 q=subprocess.run([str(bin/'dt-validate'),'-s',str(P/'schema274.json'),'-l',select,str(dtb)],capture_output=True)
 (P/('lens-schema-'+select.replace(',','-')+'-private.log')).write_bytes(q.stdout+q.stderr);checks[select]=dict(exit=q.returncode,diagnostic_bytes=len(q.stdout+q.stderr));assert q.returncode==0 and not q.stdout and not q.stderr,(select,'inspect schema diagnostics')
report=dict(stage=274,dtb_sha256=hashlib.sha256(dtb.read_bytes()).hexdigest(),new_nodes=1,existing_changed_properties=sorted([list(v) for v in changes]),sole_vaf_consumer_is_lens=True,sensor_lens_focus_phandle_valid=True,schema_validations=checks,
 soc_camss_cci_and_other_sensors_unchanged=True,board_candidate_not_deployed=True,physical_sensor_without_old_vaf_consumer_not_tested=True)
(R/'lens-board-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
