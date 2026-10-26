from pathlib import Path
import hashlib
import json
import subprocess
r = Path('/mnt/e/RealmeX2Pro edk2')
out = Path('/mnt/e/edk2-samurai-out/kernel134')
image = out / 'build-volume.ext4'
assert not Path('/home/cy122/pmos-samurai-build134').is_mount()
assert not subprocess.check_output(['losetup', '-j', str(image)], text=True).strip()
prior = json.loads((r / 'reference/kernel134/zero-hole-reclamation-validation.json').read_text())
assert prior['full_before_after_image_sha256_equal'] and prior['offline_readonly_fsck_before_after_zero']
assert not (out / 'zero-range-inventory-private.json').exists()
size = image.stat().st_size
assert size == 8 * 1024**3
chunk = 4 * 1024**2
zero = bytes(chunk)
h = hashlib.sha256()
ranges = []
start = None
offset = 0
with image.open('rb') as f:
    for data in iter(lambda: f.read(chunk), b''):
        h.update(data)
        assert len(data) == chunk
        if data == zero:
            if start is None:
                start = offset
        elif start is not None:
            ranges.append(dict(offset=start, length=offset - start))
            start = None
        offset += len(data)
if start is not None:
    ranges.append(dict(offset=start, length=offset - start))
assert offset == size and h.hexdigest() == prior['image_sha256']
assert ranges and all(0 <= x['offset'] < size and 0 < x['length'] <= size - x['offset'] for x in ranges)
(out / 'zero-range-inventory-private.json').write_text(json.dumps(dict(image_bytes=size,
    image_sha256=h.hexdigest(), ranges=ranges, all_ranges_verified_byte_zero=True,
    fixed_windows_target='E:\\edk2-samurai-out\\kernel134\\build-volume.ext4'), indent=2) + '\n')
print('K134_FIXED_VOLUME_ZERO_ONLY_RANGES_VERIFIED', len(ranges), sum(x['length'] for x in ranges), flush=True)
