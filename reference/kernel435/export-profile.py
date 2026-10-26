"""Extend selected private factory profiles with original GTM roots and axes."""
from pathlib import Path
import hashlib,json,struct,yaml
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
profile=yaml.safe_load((P.parent/'kernel431/factory-s5kgw1-private.yaml').read_text())
roots=json.loads((P.parent/'kernel432/sunny_s5kgw1-gtm-trees-private.json').read_text());selections=json.loads((P.parent/'kernel431/sunny_s5kgw1-gtm-selections-private.json').read_text())
axis=lambda name,fmt:list(struct.unpack('<'+fmt,(P.parent/'kernel432'/name).read_bytes()))
axes=dict(normalized_axis=axis('gtm-normalized-axis-private.bin','65f'),integer_axis=axis('gtm-integer-axis-private.bin','65I'),contrast_axis=axis('gtm-contrast-axis-private.bin','1024f'))
rows=[]
for mode in profile['modes']:
 match=mode['match'];index={3456:2,2592:4}[match['height']];assert match['width']==4608
 selected=next(row for tag,context,row in selections if tag=='gtm10_ife' and context[1]==index and context[2]==0)
 root=next(r for r in roots if r['tag']=='gtm10_ife' and r['uid']==selected['uid']);assert root['enabled']==1 and all(root['reserve'][k] in [0,1] for k in ['manual_curve_enable','v2_enable'])
 assert mode['ipe_tone']['tmc_enabled']==mode['ipe_tone']['tmc_use_gtm']==1
 mode['ipe_tone']['ife_gtm']=dict(enabled=bool(root['enabled']),uid=root['uid'],model='tmc11-model2',manual_curve=root['reserve']['manual_curve_enable'],v2_enable=root['reserve']['v2_enable'],**axes)
 rows.append(dict(sensor_mode_index=index,input=[match['width'],match['height']],original_selected_gtm_uid=root['uid'],original_manual_and_v2_flags_preserved=True,native_tmc11_model2_branch_reused=True,original_tmc_gtm_share_kept=True))
class NoAliasDumper(yaml.SafeDumper):
 def ignore_aliases(self,value):return True
out=P/'factory-s5kgw1-private.yaml';out.write_text(yaml.dump(profile,Dumper=NoAliasDumper,sort_keys=False))
original=yaml.safe_load((P.parent/'kernel431/factory-s5kgw1-private.yaml').read_text());restored=yaml.safe_load(out.read_text())
for mode in restored['modes']:del mode['ipe_tone']['ife_gtm']
assert restored==original
r=dict(stage=435,original_mode_selection_reused=True,original_normalized_integer_and_contrast_axes_reused=True,original_existing_profile_unchanged_except_gtm_node=True,roots=rows,profile_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),coefficients_private=True,phone_accessed=False,passed=True)
(HERE/'profile-export-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
