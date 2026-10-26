"""Fresh download namespace; old encrypted ranges stay read-only and CRC is mandatory."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ref = Path(__file__).resolve().parent
old = ref.parent / 'kernel113'
private = Path('/mnt/e/edk2-samurai-out/kernel186')
private.mkdir(exist_ok=True)
for name in ['older-realme-package-links.json', 'a11-directory-validation.json']:
    target = private / name
    assert not target.exists()
    target.write_bytes((old / name).read_bytes())
source = (old / 'inspect-a11-remote-zip.py').read_text()
source = source.replace("out=Path('/mnt/e/edk2-samurai-out/kernel113')", "out=Path('/mnt/e/edk2-samurai-out/kernel186')")
source = source.replace("ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')", "ref=Path('/mnt/e/edk2-samurai-out/kernel186')")
source = source.replace("recipe=out/'ozip-decrypt-reference-private'", "recipe=Path('/mnt/e/edk2-samurai-out/kernel113/ozip-decrypt-reference-private')")
marker = "    elif path.exists():\n        payload=path.read_bytes(); assert len(payload)==size\n"
replacement = marker + """    elif (Path('/mnt/e/edk2-samurai-out/kernel113/a11-range-cache-private') / path.name).exists():
        prior = Path('/mnt/e/edk2-samurai-out/kernel113/a11-range-cache-private') / path.name
        payload = prior.read_bytes()
        assert len(payload) == size
        path.write_bytes(payload)
"""
assert marker in source
source = source.replace(marker, replacement)
marker = 'received=0; used={}; retry_events=[]; accounting=Lock()'
assert marker in source
source = source.replace(marker, marker + "\nfetch_deadline = time.monotonic() + 1200")
marker = '    global received\n'
source = source.replace(marker, marker + "    assert time.monotonic() < fetch_deadline, 'Total download boundary reached'\n")
path = private / 'fetch-a11-ranges-private.py'
assert not path.exists()
path.write_text(source)
subprocess.run([sys.executable, '-m', 'py_compile', str(path)], check=True)
report = dict(stage=186, original113_records_and_chunks_kept=True,
    source_script_sha256=hashlib.sha256((old / 'inspect-a11-remote-zip.py').read_bytes()).hexdigest(),
    total_deadline_seconds=1200, all_ranges_require_exact_206_and_length=True,
    zip_crc_required_before_modem_acceptance=True, no_phone_write_requested=True)
(ref / 'a11-fetch-preparation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report), flush=True)
