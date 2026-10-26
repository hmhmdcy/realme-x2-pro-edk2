"""Only copy exact already-private Image502 source; no mount/helper/build call."""
from pathlib import Path
import hashlib
import json
import os
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
SOURCE = Path('/home/cy122/charging-management-20261023/gauge-image502-notify-01/source354')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert os.geteuid() == 0
evidence = json.loads((HERE.parent / 'gauge-image502-notify-candidate/build-result.json').read_bytes())
assert evidence['passed'] and evidence['build']['compatibility']['public_headers_unchanged']
cached = REF / 'charging-oem-audit-20261023/usb-input-irq-candidate/source-reference/drivers--mfd--qcom-spmi-pmic.c'
assert sha(cached) == sha(SOURCE / 'drivers/mfd/qcom-spmi-pmic.c') == 'cba250364921bfff3e8cfe10372906631cf2cba70365b2d75eabb8822084b9bd'
snapshots = HERE / 'source-reference'
snapshots.mkdir(exist_ok=True)
records = {}
for name in ['drivers/mfd/qcom-spmi-pmic.c', 'drivers/of/platform.c', 'drivers/of/device.c']:
    path = SOURCE / name
    dest = snapshots / name.replace('/', '--')
    assert not dest.exists(), 'Preserve the first source capture'
    dest.write_bytes(path.read_bytes())
    records[name] = {'sha256': sha(path), 'snapshot_sha256': sha(dest), 'bytes': path.stat().st_size}
result = {'passed': True, 'source_tree': 'exact preserved private Image502 source, ba61 plus BQ only',
          'source_tree_build_receipt_sha256': sha(HERE.parent / 'gauge-image502-notify-candidate/build-result.json'),
          'files': records, 'shared_source_read_or_written': False, 'storage_helper_invoked': False,
          'SDK_Git_build_device_used': False, 'reader_sha256': sha(Path(__file__))}
(HERE / 'source-read-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
