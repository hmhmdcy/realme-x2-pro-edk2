"""Summarize the selected profiles without publishing their coefficients."""
from pathlib import Path
import hashlib,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def leaves(nodes):
 for node in nodes:
  if 'children' in node:yield from leaves(node['children'])
  else:yield node
profiles=json.loads((P/'mode-profiles-private.json').read_text());rows=[]
for name,modes in profiles.items():
 for mode in modes:
  if mode['usecase']!='Preview':continue
  video=next(m for m in modes if m['sensor_mode_index']==mode['sensor_mode_index'] and m['usecase']=='Video')
  assert mode['modules']==video['modules']
  ccm=mode['modules']['cc13_ipe'];matrices=list(leaves(ccm['core']));identity=[1,0,0,0,1,0,0,0,1]
  ltm=mode['modules']['ltm13_ipe'];regions=list(leaves(ltm['core']))
  rows.append(dict(variant=name,sensor_mode_index=mode['sensor_mode_index'],preview_video_profiles_equal=True,
   ccm_regions=len(matrices),ccm_nonidentity_regions=sum(any(abs(a-b)>1e-6 for a,b in zip(m['matrix'],identity)) for m in matrices),
   ccm_unique_matrices=len({tuple(m['matrix']) for m in matrices}),ccm_nonzero_offsets=sum(any(m['offsets']) for m in matrices),
   ltm_regions=len(regions),ltm_nonzero_strength_regions=sum(r['data']['ltm_strength']!=0 for r in regions),
   ltm_nonzero_scale_regions=sum(any(r['data']['ltm_scale_tab']) for r in regions)))
assert all(r['ccm_nonidentity_regions']==0 for r in rows if r['variant']!='sunny_imx471')
front=next(r for r in rows if r['variant']=='sunny_imx471');assert front['ccm_nonidentity_regions']==front['ccm_regions'] and front['ccm_unique_matrices']==25
source=P/'sources/camxtitan17xsettings.xml';manifest=json.loads((HERE/'primary-sources.json').read_text())
entry=dict(path='camx/src/hwl/titan17x/'+source.name,bytes=source.stat().st_size,sha256=hashlib.sha256(source.read_bytes()).hexdigest(),url='https://github.com/bjzhou/CamxChi/blob/9f17f1b568626b393e785b369c5dc94543774d7a/camx/src/hwl/titan17x/'+source.name)
manifest['files']=[e for e in manifest['files'] if e['path']!=entry['path']]+[entry]
(HERE/'primary-sources.json').write_text(json.dumps(manifest,indent=2)+'\n')
report=dict(stage=351,selected_physical_modes=len(rows),profiles=rows,front_ife_ccm_disabled_evidence='../kernel344/README.md',
 front_colour_correction_located_in_downstream_ipe_tuning=True,not_moved_to_ife_or_enabled_in_defaults=True,
 no_claim_of_equivalence_between_ife_and_ipe_positions=True,all_coefficients_private=True,passed=True)
(HERE/'selected-profile-analysis.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
