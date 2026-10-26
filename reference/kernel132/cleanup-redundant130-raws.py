from pathlib import Path
import ast
import errno
import hashlib
import json
import os
import runpy
import shutil
import struct
import subprocess
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel132'
out = Path('/mnt/e/edk2-samurai-out/kernel132')
old = out.parent / 'kernel130'
assert json.loads((r / 'reference/kernel130/complete-bundle-validation.json').read_text())['decoded_encoded_image_actual_unprivileged_create_read_write_unlink_pass']
runpy.run_path(str(r / 'reference/kernel129/ensure-rootfs-volume.py'))
base = Path('/home/cy122/pmos-samurai-rootfs129')
assert not (out / 'redundant130-raw-cleanup-private.json').exists()
source = (r / 'reference/kernel122/cleanup-obsolete-wsl-images.py').read_text()
node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'prove')
scope = {'struct': struct, 'os': os, 'errno': errno}
exec(ast.get_source_segment(source, node), scope)
prove = scope['prove']
report = json.loads((old / 'rootfs-image-validation.json').read_text())
image = old / 'samurai-rootfs-f2fs-k130-device-fixed.simg'
h = hashlib.sha256()
with image.open('rb') as f:
    for block in iter(lambda: f.read(8 * 1024**2), b''):
        h.update(block)
assert h.hexdigest() == report['sha256'] and report['both_fsck_pass']
assert report['encoded_image_full_directory_export_and_content_metadata_check_pass']
records = []
before = shutil.disk_usage(base).free
for name in ['samurai-rootfs-f2fs-k130-device-fixed.raw.img', 'samurai-rootfs-f2fs-k130-device-fixed-restored.raw.img']:
    path = base / name
    assert path.is_file() and not path.is_symlink() and path.resolve().parent == base and path.stat().st_nlink == 1
    assert not subprocess.check_output(['losetup', '-j', str(path)], text=True).strip()
    prove(image, path)
    s = path.stat()
    records.append(dict(name=name, ino=s.st_ino, dev=s.st_dev, size=s.st_size, mtime_ns=s.st_mtime_ns, allocated=s.st_blocks * 512))
    print('K132_REDUNDANT130_RAW_FULL_PAYLOAD_AND_HOLE_RECONSTRUCTION_PROOF_PASS', name, flush=True)
(out / 'redundant130-raw-cleanup-private.json').write_text(json.dumps(records, indent=2) + '\n')
for item in records:
    path = base / item['name']
    s = path.stat()
    assert path.resolve().parent == base
    assert (s.st_ino, s.st_dev, s.st_size, s.st_mtime_ns) == (item['ino'], item['dev'], item['size'], item['mtime_ns'])
    assert not subprocess.check_output(['losetup', '-j', str(path)], text=True).strip()
    path.unlink()
assert (base / 'rootfs130').is_dir() and (base / 'image-export130-fixed').is_dir() and image.is_file()
result = dict(redundant130_raw_files_deleted=2, all_targets_fresh_byte_and_hole_reconstruction_proved=True,
              allocated_bytes_removed=sum(i['allocated'] for i in records), inner_e129_free_before=before,
              inner_e129_free_after=shutil.disk_usage(base).free, stable130_sparse_source_export_preserved=True,
              stable_kernel_sources_not_deleted=True, no_recursive_delete=True, phone_unchanged=True,
              original_wsl_vhd_not_resized_or_compacted=True, goal_complete=False)
(ref / 'redundant-raw-cleanup-validation.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result), flush=True)
