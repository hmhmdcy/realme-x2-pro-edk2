"""Verify current deployed code, services, idle camera power and vendor unmount."""
from pathlib import Path
import json
import host

previous = Path(__file__).resolve().parents[1] / 'kernel278/final-health.py'
source = previous.read_text().replace('k278-final-health', 'k281-final-health')
source = source.replace('report=dict(stage=278,', 'report=dict(stage=281,')
exec(compile(source, str(previous), 'exec'), globals())
code = r'''
from pathlib import Path
import json
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k276-work/boot-id-private.txt').read_bytes()
device=Path('/sys/class/block/sda9/dev').read_text().strip()
assert not any(line.split()[2]==device for line in Path('/proc/self/mountinfo').read_text().splitlines())
assert not Path('/run/k281-vendor-isp-static-ro').exists()
print(json.dumps(dict(vendor_unmounted=True,temporary_mountpoint_removed=True,no_reboot=True)))
'''
q = host.ssh('python3 -', input=code.encode(), timeout=15)
report = json.loads(q.stdout)
Path(__file__).with_name('vendor-unmount-validation.json').write_text(json.dumps(dict(stage=281, **report), indent=2) + '\n')
print(json.dumps(report))
