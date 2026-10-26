from pathlib import Path
import ast
import errno
import hashlib
import json
import os
import runpy
import struct
import subprocess
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel134'
out = Path('/mnt/e/edk2-samurai-out/kernel134')
assert not (out / 'sparse-fixed-validation.json').exists()
assert not (out / 'sparse-fsync-resume-private.json').exists()
runpy.run_path(str(r / 'reference/kernel129/ensure-rootfs-volume.py'))
base = Path('/home/cy122/pmos-samurai-rootfs129')
sparse = out / 'samurai-rootfs-f2fs-k134-device-fixed.simg'
source = base / 'samurai-rootfs-f2fs-k134-device-fixed.raw.img'
restored = base / 'samurai-rootfs-f2fs-k134-device-fixed-restored.raw.img'
assert source.stat().st_size == restored.stat().st_size == 119033245696
assert not subprocess.check_output(['losetup', '-j', str(restored)], text=True).strip()
with (out / 'host-dmesg-after-sparse-fsync-private.txt').open('w') as log:
    subprocess.run(['dmesg'], stdout=log, check=True)
state = {'original_failure': 'fsync ENOMEM after all chunks and final truncate', 'existing_files_only': True, 'no_reconstruction_or_pack_replay': True}
(out / 'sparse-fsync-resume-private.json').write_text(json.dumps(state, indent=2) + '\n')
with restored.open('rb') as f:
    os.fsync(f.fileno())
print('K134_EXISTING_RECONSTRUCTED_FILE_FSYNC_PASS_NO_REWRITE', flush=True)
code = (r / 'reference/kernel122/cleanup-obsolete-wsl-images.py').read_text()
node = next(n for n in ast.parse(code).body if isinstance(n, ast.FunctionDef) and n.name == 'prove')
scope = {'struct': struct, 'os': os, 'errno': errno}
exec(ast.get_source_segment(code, node), scope)
for p in [source, restored]:
    scope['prove'](sparse, p)
    print('K134_FRESH_FULL_PAYLOAD_AND_SOURCE_HOLES_PROOF_PASS', p.name, flush=True)
stats = {'raw_chunks': 0, 'fill_chunks': 0, 'skip_chunks': 0, 'crc_chunks': 0}
with sparse.open('rb') as f:
    magic, major, minor, file_h, chunk_h, block_size, blocks, chunks, checksum = struct.unpack('<I4H4I', f.read(28))
    assert magic == 0xed26ff3a and major == 1 and blocks * block_size == 119033245696
    f.seek(file_h)
    for _ in range(chunks):
        kind, reserved, nblocks, total = struct.unpack('<2H2I', f.read(12))
        stats[{0xcac1: 'raw_chunks', 0xcac2: 'fill_chunks', 0xcac3: 'skip_chunks', 0xcac4: 'crc_chunks'}[kind]] += 1
        f.seek(total - 12, 1)
    assert not f.read(1)
h = hashlib.sha256()
with sparse.open('rb') as f:
    for b in iter(lambda: f.read(8 * 1024**2), b''):
        h.update(b)
report = dict(android_sparse_magic=hex(magic), version=f'{major}.{minor}', block_size=block_size,
              expanded_bytes=blocks * block_size, expanded_gib=round(blocks * block_size / 1024**3, 4),
              sparse_bytes=sparse.stat().st_size, chunks=chunks, **stats, sha256=h.hexdigest(),
              payload_matches_raw_source=True, skipped_ranges_verified_as_source_holes=True,
              reconstructed_wsl_path=str(restored), existing_reconstruction_fsync_and_fresh_proof_pass=True)
(out / 'sparse-fixed-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('K134_EXISTING_SPARSE_RECONSTRUCTION_VALIDATION_RESUMED_PASS', flush=True)
