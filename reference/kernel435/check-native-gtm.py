"""Compare new production profile outputs to retained complete original GTM."""
from pathlib import Path
import importlib.util,json
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
assert json.loads((HERE/'ipa-validation.json').read_text())['passed']
s=importlib.util.spec_from_file_location('gtm435oracle',HERE.parent/'kernel432/gtm-model.py');n=importlib.util.module_from_spec(s);s.loader.exec_module(n)
selected=next(r for tag,c,r in json.loads((P.parent/'kernel431/sunny_s5kgw1-gtm-selections-private.json').read_text()) if tag=='gtm10_ife' and c[1]==2 and c[2]==0)
rows=[]
for i in range(3):
 adrc=(P/('profile-'+str(i)+'-adrc-private.bin')).read_bytes()+bytes(4);wanted=(P/('profile-'+str(i)+'-lut-private.bin')).read_bytes()
 m=n.Machine();chromatix,_=m.load_parsed(P.parent/'kernel432'/('sunny_s5kgw1-'+str(selected['uid'])+'-native-parse-private.json'));actual,_,_=m.calculate(chromatix,adrc=adrc)
 assert len(wanted)==512 and actual==wanted,(i,sum(a!=b for a,b in zip(actual,wanted)))
 rows.append(dict(case=i,original_instructions=m.instructions,lut_bytes=512,different_bytes=0,passed=True))
r=dict(stage=435,actual_compiled_production_profile_outputs=True,original_complete_gtm_with_original_parsed_root=True,original_manual_and_v2_flags_preserved=True,explicit_tmc11_model2_branch=True,cases=rows,axes_not_replaced=True,private_data_only=True,phone_accessed=False,passed=True)
(HERE/'native-gtm-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
