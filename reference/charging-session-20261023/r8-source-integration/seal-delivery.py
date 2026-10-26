"""Seal only source exports and offline source/patch mapping; no runtime action."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()
manifest=json.loads((HERE/'source-manifest.json').read_bytes())
checks=json.loads((HERE/'patch-check-result.json').read_bytes())
assert checks['passed'] and checks['all_three_full_base_blobs_checked']
for name,row in manifest['sources'].items():
    root='kernel-sources' if name.startswith('drivers/') else 'rootfs-sources'
    assert sha((HERE/root/name).read_bytes())==row['sha256']
files={p.relative_to(HERE).as_posix():sha(p.read_bytes()) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='delivery.json' and '__pycache__' not in p.parts}
assert not any(name.endswith(('.ko','.img','.dtb','.tar.gz')) or 'private' in Path(name).name for name in files)
receipt={'passed':True,'kind':'exact-current-r8-charging-source-integration','adapter_revision':'r8',
    'installed_manifest_sha256':manifest['installed_manifest_sha256'],'source_manifest_sha256':sha((HERE/'source-manifest.json').read_bytes()),
    'kernel_sources':12,'installed_userspace_sources':4,'files':files,
    'three_full_baseline_blobs_patch_check':True,'current_charging_source_layer_complete':True,'entire_platform_source_bundle':False,
    'existing_compilation_and_tests_reused':True,'old_tests_rerun':False,'image_built':False,'module_binaries_included':False,
    'private_originals_included':False,'private_identity_included':False,'device_accessed':False,'ssh_executed':False,
    'sdk_invoked':False,'shared_worktree_modified':False,'shared_build_modified':False,'git_index_modified':False,
    'deployed_by_this_package':False,'all_functionality_accepted':False}
(HERE/'delivery.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'passed':True,'delivery_sha256':sha((HERE/'delivery.json').read_bytes()),'source_manifest_sha256':receipt['source_manifest_sha256'],'files':len(files)}))
