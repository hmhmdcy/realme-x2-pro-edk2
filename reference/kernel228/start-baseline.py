"""Reuse the current authenticated endpoint, then require fresh native identity."""
from pathlib import Path
import json
import host

ref = Path(__file__).resolve().parent
endpoint = host.PRIVATE / 'usb-ipv6-candidates-private.json'
assert not endpoint.exists()
endpoint.write_bytes((host.PRIVATE.parent / 'kernel226/usb-ipv6-candidates-private.json').read_bytes())
(host.PRIVATE / 'preboot-usb-peer-private.json').write_bytes(endpoint.read_bytes())
result = host.ssh('python3 -', input=(ref / 'collect-baseline.py').read_bytes(), timeout=100)
(host.PRIVATE / 'baseline-host-private.log').write_bytes(result.stdout + result.stderr)
report = json.loads(result.stdout)
(ref / 'baseline-validation.json').write_text(json.dumps(report, indent=2) + '\n')
(host.PRIVATE / 'current-work-private.json').write_text(json.dumps(dict(
    stage=228, state='fresh baseline verified; candidate not installed',
    guard='/var/lib/samurai/k228-baseline/boot-id-private.txt', full_peripheral_goal_active=True,
    previous_goal_turn_classification='progress: final candidate, exact embedded-initramfs proof and11 extracted-function tests',
    transition_pending=False, active_native_session=None), indent=2) + '\n')
print(json.dumps(report))
