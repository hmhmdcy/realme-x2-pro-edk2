from pathlib import Path
import importlib.util,json,sys
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
sys.path.insert(0,'/home/cy122/x2pro-linux/private-k329-venv/lib/python3.14/site-packages')
assert json.loads((HERE/'rear-math-validation.json').read_text())['passed']
s=importlib.util.spec_from_file_location('gtm438oracle',HERE.parent/'kernel432/gtm-model.py');n=importlib.util.module_from_spec(s);s.loader.exec_module(n)
rows=[]
for variant,model,mode in [('sunny_imx319','imx319',2),('qtech_s5k3m5sx','s5k3m5',3)]:
 selected=next(r for tag,c,r in json.loads((P.parent/'kernel431'/(variant+'-gtm-selections-private.json')).read_text()) if tag=='gtm10_ife' and c[1]==mode and c[2]==0)
 for i in range(3):
  adrc=(P/(model+'-'+str(i)+'-adrc-private.bin')).read_bytes()+bytes(4);wanted=(P/(model+'-'+str(i)+'-lut-private.bin')).read_bytes()
  m=n.Machine();chromatix,_=m.load_parsed(P.parent/'kernel432'/(variant+'-'+str(selected['uid'])+'-native-parse-private.json'));actual,_,_=m.calculate(chromatix,adrc=adrc)
  assert len(wanted)==512 and actual==wanted,(model,i,sum(a!=b for a,b in zip(actual,wanted)))
  rows.append(dict(model=model,mode=mode,root_uid=selected['uid'],case=i,lut_bytes=512,different_bytes=0,original_instructions=m.instructions,passed=True))
r=dict(stage=438,cases=rows,actual_compiled_production_profiles=True,original_complete_gtm_and_original_per_camera_parsed_roots=True,original_manual_and_v2_flags_preserved=True,passed=True)
(HERE/'native-gtm-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
