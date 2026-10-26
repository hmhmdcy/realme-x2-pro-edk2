"""Bind the retained stock mode4 DS4 pass to the existing 16:9 main profile."""
from pathlib import Path
import copy,hashlib,json,struct,yaml
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
original=(P.parent/'kernel440/factory-s5kgw1-private.yaml').read_text()
expected=json.loads((HERE.parent/'kernel437/profile-export-validation.json').read_text())['profile_sha256']
assert hashlib.sha256(original.encode()).hexdigest()==expected
profile=yaml.safe_load(original);assert [m['match']['height'] for m in profile['modes']]==[3456,2592]
assert 'ife_ds4' in profile['modes'][0] and 'ife_ds4' not in profile['modes'][1]
proof=json.loads((HERE.parent/'kernel426/sunny_s5kgw1-ds4-extraction-validation.json').read_text())
assert proof['passed'] and proof['all_binary_reserves_match_oem_parser_xml'] and proof['all_mode_queries_match_original_manager']
selections=json.loads((P.parent/'kernel426/sunny_s5kgw1-ds4-selection-private.json').read_text())
roots=json.loads((P.parent/'kernel426/sunny_s5kgw1-ds4-reserves-private.json').read_text())
contexts=[s for s in selections if s['sensor_mode_index']==4 and s['tag']=='ds4to1v10_ife_full_dc4']
assert {s['usecase'] for s in contexts}=={'Preview','Video'}
values=[]
for selected in contexts:
 root=next(r for r in roots if r['uid']==selected['uid'] and r['tag']==selected['tag'])
 full=next(r for r in root['passes'] if r[0]==0);values.append(full[1:])
assert values[0]==values[1];coefficients=values[0]
assert len(coefficients)==3 and all(0<=c<=256 for c in coefficients) and 256<=sum(coefficients)<=512
parts=original.split('- match:');assert len(parts)==3 and parts[2].count('  ipe_tone:')==1
parts[2]=parts[2].replace('  ipe_tone:','  ife_ds4:\n'+''.join('  - '+str(c)+'\n' for c in coefficients)+'  ipe_tone:',1)
exported='- match:'.join(parts);after=yaml.safe_load(exported);restored=copy.deepcopy(after)
assert restored['modes'][1].pop('ife_ds4')==coefficients and restored==profile
(P/'factory-s5kgw1-private.yaml').write_text(exported)
(P/'expected-mode4-ds4-private.bin').write_bytes(struct.pack('<HHI4H',8,0,16,*coefficients,0))
r=dict(stage=443,source_stage=426,sensor_mode_index=4,input=[4608,2592],original_preview_video_selections_agree=True,
 original_pass_full_coefficients_used=True,existing_oem_parser_and_manager_proofs_reused=True,
 only_new_mode2592_ife_ds4_key=True,mode3456_and_all_other_tuning_unchanged=True,
 baseline_sha256=expected,profile_sha256=hashlib.sha256(exported.encode()).hexdigest(),coefficients_private=True,
 installed=False,phone_accessed=False,passed=True)
(HERE/'profile-export-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
