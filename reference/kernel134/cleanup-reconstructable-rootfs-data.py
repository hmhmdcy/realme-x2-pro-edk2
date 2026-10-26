from pathlib import Path
import ast
import errno
import hashlib
import json
import os
import runpy
import shutil
import stat
import struct
import subprocess
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel134'
out = Path('/mnt/e/edk2-samurai-out/kernel134')
assert not (ref / 'rootfs-space-cleanup-validation.json').exists()
runpy.run_path(str(r / 'reference/kernel129/ensure-rootfs-volume.py'))
base = Path('/home/cy122/pmos-samurai-rootfs129')
def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for data in iter(lambda: f.read(8 * 1024**2), b''):
            h.update(data)
    return h.hexdigest()
code = (r / 'reference/kernel122/cleanup-obsolete-wsl-images.py').read_text()
node = next(n for n in ast.parse(code).body if isinstance(n, ast.FunctionDef) and n.name == 'prove')
scope = {'struct': struct, 'os': os, 'errno': errno}
exec(ast.get_source_segment(code, node), scope)
prove = scope['prove']
code = (r / 'reference/kernel130/verify-image-export-fixed.py').read_text()
node = next(n for n in ast.parse(code).body if isinstance(n, ast.FunctionDef) and n.name == 'manifest')
scope = {'Path': Path, 'os': os, 'stat': stat, 'hashlib': hashlib, 'sha': sha}
exec(ast.get_source_segment(code, node), scope)
manifest = scope['manifest']
before_free = shutil.disk_usage(base).free
raws = []
image = out.parent / 'kernel132/samurai-rootfs-f2fs-k132-device-fixed.simg'
report = json.loads((out.parent / 'kernel132/rootfs-image-validation.json').read_text())
assert sha(image) == report['sha256'] and report['both_fsck_pass']
assert report['encoded_image_full_directory_export_and_content_metadata_check_pass']
for name in ['samurai-rootfs-f2fs-k132-device-fixed.raw.img', 'samurai-rootfs-f2fs-k132-device-fixed-restored.raw.img']:
    p = base / name
    assert p.is_file() and not p.is_symlink() and p.resolve().parent == base and p.stat().st_nlink == 1
    assert not subprocess.check_output(['losetup', '-j', str(p)], text=True).strip()
    prove(image, p)
    s = p.stat()
    raws.append(dict(name=name, inode=s.st_ino, device=s.st_dev, size=s.st_size, mtime_ns=s.st_mtime_ns,
                     allocated=s.st_blocks * 512))
    print('K134_LATEST132_RAW_RECONSTRUCTION_FULL_PAYLOAD_AND_HOLES_PASS', name, flush=True)
exports = []
source_manifests = {}
for generation in [129, 130]:
    root = base / ('rootfs' + str(generation))
    export = base / ('image-export' + str(generation) + '-fixed')
    assert export.resolve().parent == base and not export.is_symlink() and export.is_dir() and root.is_dir()
    assert not any(Path(line).is_relative_to(export.resolve()) for line in subprocess.check_output(['findmnt', '-rn', '-o', 'TARGET'], text=True).splitlines())
    original = manifest(root)
    extracted = manifest(export)
    assert original == extracted
    stable = out.parent / ('kernel' + str(generation)) / f'samurai-rootfs-f2fs-k{generation}-device-fixed.simg'
    stable_report = json.loads((stable.parent / 'rootfs-image-validation.json').read_text())
    assert sha(stable) == stable_report['sha256'] and stable_report['both_fsck_pass']
    assert stable_report['encoded_image_full_directory_export_and_content_metadata_check_pass']
    allocated = sum(p.lstat().st_blocks * 512 for p in export.rglob('*') if not p.is_symlink())
    exports.append(dict(generation=generation, name=export.name, entries=len(original),
                        content_and_metadata_equal_retained_source=True, stable_sparse_hash_reverified=True,
                        allocated=allocated))
    source_manifests[generation] = original
    print('K134_OLD_EXPORT_FULL_CONTENT_METADATA_AND_STABLE_SPARSE_PROOF_PASS', generation, flush=True)
(out / 'rootfs-space-cleanup-inventory-private.json').write_text(json.dumps(dict(raws=raws, exports=exports), indent=2) + '\n')
for item in raws:
    p = base / item['name']
    s = p.stat()
    assert (s.st_ino, s.st_dev, s.st_size, s.st_mtime_ns) == (item['inode'], item['device'], item['size'], item['mtime_ns'])
    assert not subprocess.check_output(['losetup', '-j', str(p)], text=True).strip()
    p.unlink()
for item in exports:
    export = base / item['name']
    root = base / ('rootfs' + str(item['generation']))
    assert export.resolve().parent == base and not export.is_symlink()
    assert manifest(root) == manifest(export) == source_manifests[item['generation']]
    shutil.rmtree(export)
    assert manifest(root) == source_manifests[item['generation']] and not export.exists()
assert (base / 'rootfs132').is_dir() and (base / 'image-export132-fixed').is_dir() and image.is_file()
result = dict(stage=134, latest132_redundant_raws_deleted=2, full_raw_payload_and_holes_reconstruction_proved=True,
    old129_130_exports_deleted=2, old_export_content_and_metadata_equals_retained_sources=True,
    old_stable_sparse_hashes_freshly_verified=True, all129_130_132_sources_and_stable_sparse_images_retained=True,
    latest132_export_retained=True, allocated_bytes_removed=sum(x['allocated'] for x in raws + exports),
    inner_e129_before_free_bytes=before_free, inner_e129_after_free_bytes=shutil.disk_usage(base).free,
    every_recursive_target_resolved_inside_verified_private_rootfs_volume=True,
    original_wsl_vhd_not_resized_or_compacted=True, phone_unchanged=True, goal_complete=False)
(ref / 'rootfs-space-cleanup-validation.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result), flush=True)
