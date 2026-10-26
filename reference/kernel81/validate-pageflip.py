from pathlib import Path
import hashlib
import json
import re

out = Path('/mnt/e/edk2-samurai-out/kernel81')
raw = (out / 'pageflip-after-timeouts.txt').read_bytes()
rows = [tuple(int(word, 0) for word in match) for match in re.findall(
    r'sample=(\d+) pattern=(\d+) event=(\d+) scanout CRC (0x[0-9a-f]+) (0x[0-9a-f]+) (0x[0-9a-f]+)', raw.decode())]
expected = {0: (0x69961448, 0x60af15f5), 1: (0x25e11871, 0x25e11871)}
assert rows
assert all(row[4:] in expected.values() for row in rows)
grouped = {}
for row in rows:
    grouped.setdefault(row[0], []).append(row)
assert list(grouped) == list(range(600))
confirmed = [values[-1] for values in grouped.values()]
assert all(row[1] == (row[0] & 1) and row[4:] == expected[row[1]] for row in confirmed)
assert all(b[2] > a[2] for a,b in zip(confirmed, confirmed[1:]))
assert all(b[3] > a[3] for a,b in zip(confirmed, confirmed[1:]))
text = raw.decode()
assert 'No panel power cycle requested; original CRTC restored directly' in text
assert 'Native KMS mode setting, scanout/vblank and console restoration passed' in text
result = {
    'pageflip_sha256': hashlib.sha256(raw).hexdigest(),
    'completed_page_flips': len(grouped), 'crc_rows': len(rows),
    'requested_patterns_confirmed': len(confirmed),
    'all_crc_rows_match_one_of_two_immutable_buffers': True,
    'flip_event_and_confirmed_crc_sequences_monotonic': True,
    'elapsed_seconds': float(re.search(r'600 page flips elapsed=([0-9.]+)', text)[1]),
    'no_explicit_crtc_disable_or_panel_power_cycle': True,
    'physical_optical_observation': False,
}
(out / 'pageflip-after-timeouts-validation.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
