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
assert not (out / 'sparse-repair-r1-private.json').exists()
assert not (out / 'sparse-fixed-validation.json').exists()
runpy.run_path(str(r / 'reference/kernel129/ensure-rootfs-volume.py'))
base = Path('/home/cy122/pmos-samurai-rootfs129')
sparse = out / 'samurai-rootfs-f2fs-k134-device-fixed.simg'
source = base / 'samurai-rootfs-f2fs-k134-device-fixed.raw.img'
restored = base / 'samurai-rootfs-f2fs-k134-device-fixed-restored.raw.img'
assert restored.resolve().parent == base and not restored.is_symlink() and restored.stat().st_nlink == 1
assert source.stat().st_size == restored.stat().st_size == 119033245696
assert not subprocess.check_output(['losetup', '-j', str(restored)], text=True).strip()
digest = lambda b: hashlib.sha256(b).hexdigest()
repairs = []
with sparse.open('rb') as f, source.open('rb') as original, restored.open('rb') as target:
    magic, major, minor, fh, ch, bs, blocks, chunks, crc = struct.unpack('<I4H4I', f.read(28))
    assert magic == 0xed26ff3a and major == 1 and bs == 4096 and blocks * bs == 119033245696
    f.seek(fh)
    offset = 0
    for _ in range(chunks):
        kind, reserved, n, total = struct.unpack('<2H2I', f.read(12))
        f.seek(ch - 12, 1)
        size = n * bs
        assert offset + size <= source.stat().st_size
        if kind == 0xcac3:
            assert total == ch
            for file in [original, target]:
                try:
                    next_data = os.lseek(file.fileno(), offset, os.SEEK_DATA)
                except OSError as e:
                    assert e.errno == errno.ENXIO
                    next_data = blocks * bs
                assert next_data >= offset + size
        elif kind in [0xcac1, 0xcac2]:
            pattern = f.read(4) if kind == 0xcac2 else None
            assert total == ch + (4 if pattern is not None else size)
            for step_offset in range(0, size, 4 * 1024**2):
                step = min(size - step_offset, 4 * 1024**2)
                input_offset = f.tell()
                expected = pattern * (step // 4) if pattern is not None else f.read(step)
                position = offset + step_offset
                original.seek(position)
                target.seek(position)
                assert len(expected) == step and original.read(step) == expected
                actual = target.read(step)
                if actual != expected:
                    repairs.append(dict(offset=position, size=step, sparse_offset=input_offset,
                                        pattern=pattern.hex() if pattern is not None else None,
                                        before_sha256=digest(actual), expected_sha256=digest(expected)))
        elif kind == 0xcac4:
            assert n == 0 and total == ch + 4
            f.read(4)
        else:
            raise ValueError(kind)
        offset += size
    assert offset == blocks * bs and not f.read(1)
assert repairs, 'Fresh mismatch not reproduced; do not mutate'
identity = restored.stat()
record = dict(failed_reconstruction_inode=identity.st_ino, failed_reconstruction_size=identity.st_size,
              verified_source_payload_and_holes=True, mismatches=repairs, repaired_bytes=sum(x['size'] for x in repairs))
(out / 'sparse-repair-r1-private.json').write_text(json.dumps(record, indent=2) + '\n')
print('K134_FAILED_RECONSTRUCTION_MISMATCHES_IDENTIFIED', len(repairs), record['repaired_bytes'], flush=True)
with sparse.open('rb') as f, source.open('rb') as original, restored.open('r+b', buffering=0) as target:
    assert os.fstat(target.fileno()).st_ino == identity.st_ino
    for item in repairs:
        f.seek(item['sparse_offset'])
        expected = bytes.fromhex(item['pattern']) * (item['size'] // 4) if item['pattern'] is not None else f.read(item['size'])
        original.seek(item['offset'])
        target.seek(item['offset'])
        assert digest(expected) == item['expected_sha256'] and original.read(item['size']) == expected
        assert digest(target.read(item['size'])) == item['before_sha256']
        assert os.pwrite(target.fileno(), expected, item['offset']) == item['size']
    os.fsync(target.fileno())
code = (r / 'reference/kernel122/cleanup-obsolete-wsl-images.py').read_text()
node = next(n for n in ast.parse(code).body if isinstance(n, ast.FunctionDef) and n.name == 'prove')
scope = {'struct': struct, 'os': os, 'errno': errno}
exec(ast.get_source_segment(code, node), scope)
scope['prove'](sparse, restored)
assert restored.stat().st_size == identity.st_size and restored.stat().st_ino == identity.st_ino
print('K134_REPAIRED_EXISTING_RECONSTRUCTION_FRESH_FULL_PAYLOAD_AND_HOLES_PASS', flush=True)
tail = (ref / 'resume-sparse-after-fsync.py').read_text().split("stats = {'raw_chunks':", 1)[1]
exec("stats = {'raw_chunks':" + tail)
(ref / 'sparse-reconstruction-repair-validation.json').write_text(json.dumps(dict(
    original_fsync_enomem_preserved=True, subsequent_readonly_proof_detected_missing_payload=True,
    source_raw_and_sparse_payload_freshly_identical=True, existing_failed_reconstruction_repaired_only=True,
    repaired_ranges=len(repairs), repaired_bytes=record['repaired_bytes'], file_inode_and_size_preserved=True,
    final_fsync_and_fresh_full_payload_holes_proof_pass=True, no_pack_or_source_mutation=True,
    phone_unchanged=True, goal_complete=False), indent=2) + '\n')
