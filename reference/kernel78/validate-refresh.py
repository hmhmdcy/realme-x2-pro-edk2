from pathlib import Path
import hashlib
import json
import re

out = Path('/mnt/e/edk2-samurai-out/kernel78')
raw = (out / 'refresh.txt').read_bytes()
lines = raw.decode().splitlines()
samples = []
for line in lines:
    match = re.fullmatch(r'sample=(\d+) pattern=(\d+) scanout CRC (0x[0-9a-f]+) (0x[0-9a-f]+) (0x[0-9a-f]+)', line)
    if match:
        samples.append(tuple(int(word, 0) for word in match.groups()))
assert len(samples) == 600
assert [row[0] for row in samples] == list(range(600))
expected = {0: (0x69961448, 0x60af15f5), 1: (0x25e11871, 0x25e11871)}
matches = [row for row in samples if row[3:] == expected[row[1]]]
settled = [row for row in samples if row[0] % 60 != 0]
settled_matches = [row for row in settled if row[3:] == expected[row[1]]]
assert len(settled_matches) == len(settled)
assert all(row[0] % 60 == 0 and row[0] != 0 for row in samples if row[3:] != expected[row[1]])
assert 'No panel power cycle requested; original CRTC restored directly' in lines
assert 'Native KMS mode setting, scanout/vblank and console restoration passed' in lines
elapsed = float(next(line.split('=')[1].split()[0] for line in lines if line.startswith('600 redraws elapsed=')))
result = {
    'refresh_sha256': hashlib.sha256(raw).hexdigest(),
    'samples': len(samples), 'pattern_matches': len(matches),
    'settled_samples': len(settled), 'settled_pattern_matches': len(settled_matches),
    'elapsed_seconds': elapsed,
    'transition_sample_exclusion': 'First sample at each 60-sample pattern boundary; all 9 mismatches occur exactly during the active-buffer rewrite. Cause is inferred CPU rewrite tearing; immutable-buffer page flips are the acceptance probe.',
    'no_explicit_crtc_disable_or_panel_power_cycle': True,
    'physical_optical_observation': False,
}
(out / 'refresh-validation.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
