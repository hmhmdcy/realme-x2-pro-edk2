"""Read cached DTBs and fixed source linkage; never run their generators."""
from pathlib import Path
import ast,hashlib,json,struct
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
legacy=REF/'kernel93/verify-firmware.py';code=legacy.read_text()
node=next(n for n in ast.parse(code).body if isinstance(n,ast.FunctionDef) and n.name=='fdt_nodes')
env={'struct':struct,'align':lambda n,a:(n+a-1)//a*a}
exec(compile(ast.Module(body=[node],type_ignores=[]),'actual-frozen-fdt-reader','exec'),env)
native=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/usb-dt/samurai-charging-usb-private.dtb')
candidate_meta=REF/'charging-oem-audit-20261023/eud-boot-policy/candidate-result.json'
meta=json.loads(candidate_meta.read_bytes());candidate=Path(meta['native_candidate_path'])
assert sha(native)=='c559d2c4c9a83e85473b1b24724bb8938f1084bd3efcae9c4b67f37c2a4c4503'
assert sha(candidate)==meta['native_candidate_sha256']=='9271d9cc33b3701ad0675c6345d43e9a5c404aa6c192126edc3eb715b0914358'
a,b=env['fdt_nodes'](native.read_bytes()),env['fdt_nodes'](candidate.read_bytes())
typec='/soc@0/spmi@c440000/pmic@2/typec@1500'
vbus='/soc@0/spmi@c440000/pmic@2/usb-vbus-regulator@1100'
paths=[p for p in a if p==typec or p.startswith(typec+'/') or p==vbus]
assert paths and all(a[p]==b[p] for p in paths)
nodes={p:{k:v.hex() for k,v in a[p].items()} for p in paths}
link_path=REF/'charging-oem-audit-20261023/apsd-integration/current-r7/image-source-linkage.json'
link=json.loads(link_path.read_bytes());manifest=json.loads((HERE/'source-manifest.json').read_bytes())
qcom=[]
for row in manifest['files']:
 if not row['path'].endswith('.c') or 'qcom/' not in row['path']:continue
 if row['path'].endswith('_stub.c'):continue
 item=next(x for x in link['comparisons'] if x['path']==row['path'])
 assert row['sha256']==item['base_sha256']==item['current_sha256'] and item['byte_equal_to_original_image_source']
 qcom.append(row['path'])
result=dict(passed=True,dtb_sha256=sha(native),boot_policy_dtb_sha256=sha(candidate),
 selected_typec_nodes=nodes,TypeC_subtree_unchanged_by_EUD_boot_policy=True,
 typec_status=a[typec]['status'].decode().rstrip('\0'),
 typec_children=[p for p in paths if p.startswith(typec+'/')],
 qcom_source_bytes_equal_original_Image363=qcom,
 tcpm_core_current_source_fixed_but_independent_ba61_byte_link_not_claimed=True,
 reference_hashes={str(p.relative_to(REF)):sha(p) for p in [legacy,link_path,candidate_meta]},
 device_accessed=False,SDK_invoked=False,Git_invoked=False,shared_files_modified=False)
(HERE/'board-linkage.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(passed=True,typec_status=result['typec_status'],typec_children=result['typec_children'],qcom_source_count=len(qcom))))
