"""Validate the binding and real DTB, including rejected incomplete fixtures."""
from pathlib import Path
import json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;tools=P/'schema-venv/bin'
schema=P/'Documentation/devicetree/bindings/media/qcom,sm8150-camss-icp.yaml';schema.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE/schema.name,schema)
def run(args,label,good=True):
 q=subprocess.run([str(tools/args[0]),*map(str,args[1:])],capture_output=True)
 text=(q.stdout+q.stderr).decode(errors='replace');(P/(label+'.log')).write_text(text)
 assert (not text.strip() and q.returncode==0) if good else bool(text.strip()),(label,q.returncode,text[-5000:])
 return text
run(['dt-doc-validate',schema],'binding-doc')
run(['dt-validate','-s',schema,'-l','qcom,sm8150-camss-icp',P/'samurai389-private.dtb'],'binding-dtb')
code=r'''from pathlib import Path
import libfdt
root=Path(ROOT);data=(root/'samurai389-private.dtb').read_bytes()
for name in ['six-iommus','missing-memory','unexpected-property','empty-firmware']:
 f=libfdt.Fdt(data);f.resize(len(data)+512);node=f.path_offset('/soc@0/icp@ac10000')
 if name=='six-iommus':f.setprop(node,'iommus',bytes(f.getprop(node,'iommus'))[:-12])
 elif name=='missing-memory':f.delprop(node,'memory-region')
 elif name=='empty-firmware':f.setprop(node,'firmware-name',b'\0')
 else:f.setprop(node,'unexpected-property',b'')
 f.pack();(root/('negative-'+name+'.dtb')).write_bytes(f.as_bytearray())
'''.replace('ROOT',repr(str(P)))
q=subprocess.run([str(tools/'python'),'-c',code],capture_output=True);assert not q.returncode,q.stderr.decode()
negative=[]
for name in ['six-iommus','missing-memory','unexpected-property','empty-firmware']:
 text=run(['dt-validate','-s',schema,'-l','qcom,sm8150-camss-icp',P/('negative-'+name+'.dtb')],'binding-negative-'+name,False)
 assert 'icp@ac10000' in text and 'qcom,sm8150-camss-icp.yaml' in text
 negative.append(dict(name=name,rejected=True))
report=dict(stage=389,dt_schema_versions=json.loads((P/'schema-versions.json').read_text()),binding_meta_schema_valid=True,actual_candidate_dtb_passes_icp_binding=True,negative_fixtures=negative,scope='only the new ICP binding plus separately checked full DT semantic preservation; not all board bindings or upstream review',passed=True)
(HERE/'binding-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
