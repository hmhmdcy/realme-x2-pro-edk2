"""Prepare a fresh live transaction from the locked235 staged candidate."""
from pathlib import Path
import hashlib
import json

R = Path(__file__).resolve().parent
P = Path('/mnt/e/edk2-samurai-out/kernel236')
assert not P.exists()
P.mkdir(mode=0o700)
previous = P.parent / 'kernel235'
lock = json.loads((previous / 'deployment-lock-private.json').read_text())
for info in lock['files'].values():
    path = Path(info['path'])
    assert path.stat().st_size == info['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest() == info['sha256']
(P / 'deployment-lock-private.json').write_text(json.dumps(lock, indent=2) + '\n')
(P / 'build-package-validation.json').write_bytes((previous / 'build-package-validation.json').read_bytes())
(P / 'usb-ipv6-candidates-private.json').write_bytes((previous / 'usb-ipv6-candidates-private.json').read_bytes())
host = (R.parent / 'kernel235/host.py').read_text().replace('kernel235', 'kernel236').replace('usb235', 'usb236').replace('Authenticated234', 'Authenticated236')
(R / 'host.py').write_text(host)
state = dict(stage=236, state='prepared fresh236 namespace; current233 guard,235 disk staging; no transition begun',
             guard='/var/lib/samurai/k233-runtime/boot-id-private.txt', transition_pending=False,
             active_native_context=None, active_build_session=None,
             previous_goal_turn_classification='progress', front_known_colour_test_deferred_by_user=True,
             full_peripheral_goal_active=True, next='Fresh baseline then prepare audited transition preserving live P/Q/provider')
(P / 'current-work-private.json').write_text(json.dumps(state, indent=2) + '\n')
print(json.dumps(dict(stage=236, locked_artifacts=len(lock['files']), fresh_namespace_prepared=True, phone_untouched=True)))
