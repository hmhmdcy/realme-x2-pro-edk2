"""Compare existing DT semantics across deterministic phandle renumbering."""
from pathlib import Path
import hashlib,json,re
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
ns={};exec((HERE.parent/'kernel93/verify-firmware.py').read_text().split('\ndt_audit=')[0],ns)
old=P/'dtb-before-private.dtb';new=P/'samurai365-private.dtb';before=ns['fdt_nodes'](old.read_bytes());nodes=ns['fdt_nodes'](new.read_bytes())
assert set(nodes)-set(before)=={'/soc@0/icp@ac10000'} and not set(before)-set(nodes)
handles=lambda tree:{int.from_bytes(props['phandle'],'big'):path for path,props in tree.items() if 'phandle' in props}
old_handles=handles(before);new_handles=handles(nodes)
changed={p:[key for key in before[p].keys()|nodes[p].keys() if before[p].get(key)!=nodes[p].get(key)] for p in before}
changed={p:keys for p,keys in changed.items() if keys}
reference_properties={'clocks','assigned-clocks','assigned-clock-parents','memory-region','remote-endpoint','interconnects','power-domains','interrupt-parent','operating-points-v2','required-opps','phys','io-channels','thermal-sensors','trip','cooling-device','sound-dai','remoteproc','gpio-ranges'}
renumbered_cells=0
reference_properties.update({'interrupts-extended','dmas','qcom,smem-states','slim-ifc-dev'})
for path,keys in changed.items():
 for key in keys:
  a=before[path].get(key);b=nodes[path].get(key)
  if key=='phandle':
   assert path=='/reserved-memory/memory@9ab00000' or (a is not None and b is not None)
   assert new_handles[int.from_bytes(b,'big')]==path
   if a is not None:assert old_handles[int.from_bytes(a,'big')]==path
   continue
  assert key in reference_properties or key.endswith('-supply') or re.fullmatch(r'pinctrl-\d+',key),(path,key)
  assert a is not None and b is not None and len(a)==len(b) and len(a)%4==0
  for i in range(0,len(a),4):
   x=int.from_bytes(a[i:i+4],'big');y=int.from_bytes(b[i:i+4],'big')
   if x==y:continue
   assert x in old_handles and y in new_handles and old_handles[x]==new_handles[y],(path,key,i)
   renumbered_cells+=1
icp=nodes['/soc@0/icp@ac10000'];camera=nodes['/reserved-memory/memory@9ab00000']
assert icp['status']==b'disabled\0' and icp['memory-region']==camera['phandle'] and camera['phandle']!=bytes(4)
assert icp['memory-region-names']==b'firmware\0' and 'no-map' in camera
assert camera['reg']==before['/reserved-memory/memory@9ab00000']['reg']
old_package=json.loads((HERE.parent/'kernel363/boot-package-validation.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(P.parent/'kernel363/Image-k363-private')==old_package['image_sha256']
state=json.loads((HERE/'source-state.json').read_text())
report=dict(stage=365,commit=state['commit'],passed=True,dtb_sha256=sha(new),dtb_bytes=new.stat().st_size,
    old_dtb_sha256=sha(old),added_nodes=['/soc@0/icp@ac10000'],existing_node_semantic_changes={'/reserved-memory/memory@9ab00000':['phandle added']},
    renumbered_reference_cells=renumbered_cells,all_existing_phandle_references_preserve_target_paths=True,
    all_other_existing_dt_properties_semantically_identical=True,firmware_phandle=int.from_bytes(camera['phandle'],'big'),
    firmware_reg_and_no_map_preserved=True,icp_disabled=True,kernel_image_sha256=old_package['image_sha256'],
    kernel_image_stage=363,module_release=old_package['release'],kernel_image_or_modules_rebuilt=False,not_deployed=True,
    diagnostics=[l for l in (P/'dt-build-private.log').read_text(errors='replace').splitlines() if 'warning:' in l.lower() or 'error:' in l.lower()])
assert not report['diagnostics']
(HERE/'dt-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
