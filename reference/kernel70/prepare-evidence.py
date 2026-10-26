"""Prepare metadata for saved evidence; no target access or source edits."""
from pathlib import Path
import hashlib, json, re, subprocess

out = Path('/mnt/e/edk2-samurai-out/kernel70')
workspace = Path('/mnt/e/RealmeX2Pro edk2')
captures = {}
for name, frames, acked, native, retries, marker in [
    ('mode-receipt', 270, 85, 6, 1, 'K70F'),
    ('cmd-db-save', 922, 354, 26, 0, 'K70CS'),
    ('cmd-db', 610, 66, 5, 0, 'K70CE'),
    ('provider-state-save', 862, 328, 24, 0, 'K70SS'),
    ('provider-state', 356, 66, 5, 0, 'K70SE'),
    ('latest-dmesg-save', 353, 113, 8, 0, 'K70LS'),
    ('latest-dmesg', 6382, 66, 5, 1, 'K70LE'),
    ('runtime-facts-save', 867, 335, 24, 1, 'K70PS'),
    ('runtime-facts', 304, 66, 5, 1, 'K70PE'),
]:
    captures[name] = dict(frames=frames, acked_bytes=acked, native_data_frames=native,
        retries=retries, close_observed=True, exit_code=0, stray=0, buffered_bytes=0, end_marker=marker)
(out / 'windows-close-observations.json').write_text(json.dumps({'source': 'Observed tool stdout/stderr close lines; raw/events are separately verified.', 'captures': captures}, indent=2) + '\n')
preserved = json.loads((workspace / 'reference/kernel69/source-preservation.json').read_text())
for path, digest in preserved.items():
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
(out / 'source-preservation.json').write_text(json.dumps(preserved, indent=2) + '\n')
image = Path('/mnt/e/edk2-samurai-out/logdump-k67-usb.img')
image_sha = hashlib.sha256(image.read_bytes()).hexdigest()
assert image_sha == 'cfbe4509da3e4455351c11cad6400af7cc4044f21cc3ba04e3927bd01c35e6d7'
listing = subprocess.check_output(['mdir', '-i', str(image), '::']).decode()
(out / 'logdump-offline-mdir.txt').write_text(listing)
free = int(re.search(r'([\d ]+) bytes free', listing).group(1).replace(' ', ''))
capacity = dict(source=str(image), image_bytes=image.stat().st_size, image_sha256=image_sha,
    free_bytes=free, free_mib=free / 1048576, kernel_image_bytes=30185984, fat_dtb_bytes=94803,
    limit='Read-only inspection of preserved offline image; no new phone filesystem/GPT write or scan.')
(out / 'filesystem-capacity.json').write_text(json.dumps(capacity, indent=2) + '\n')
result = subprocess.run(['python3', str(out / 'verify.py')], text=True, capture_output=True)
if result.returncode:
    print(result.stderr)
    raise SystemExit(result.returncode)
(out / 'verification-report.json').write_text(result.stdout)
report = json.loads(result.stdout)
print(json.dumps({'captures_verified': len(report['captures']), 'exports': report['exports'],
    'cmd_db': report['cmd_db'], 'logdump_free_bytes': free, 'source_preservation_pass': True}, indent=2))
