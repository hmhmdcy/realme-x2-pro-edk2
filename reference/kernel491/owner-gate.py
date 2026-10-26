"""Fresh camera handoff validation; importing this file performs no I/O."""
from datetime import datetime, timezone
from pathlib import Path
import os
import re


def authorization(plan, now):
    assert plan['deployable'] and plan['window_id'] == WINDOW
    assert re.fullmatch(r'k491-package-only-r[1-9][0-9]*', WINDOW)
    handoff, owner, scoped = [plan[key] for key in ['handoff', 'owner', 'scoped_owner']]
    preflight = plan['preflight_window_id']
    assert re.fullmatch(r'k476-control-delay-r([1-9]|1[0-9]|20)', preflight)
    assert handoff['fresh_preflight_verified'] and handoff['window_owner'] == 'camera'
    assert handoff['window_id'] == preflight
    for record, maximum in [(handoff, 600), (owner, 480), (scoped, 480)]:
        age = (now - datetime.fromisoformat(record['issued_at_utc'].replace('Z', '+00:00'))).total_seconds()
        assert 0 <= age <= maximum, ('stale authorization', age)
    assert owner['authorized_window_ids'] == [preflight, WINDOW]
    assert scoped['authorized_window_ids'] == [preflight]
    ignored = {'authorized_window_ids', 'issued_at_utc'}
    assert {key: value for key, value in owner.items() if key not in ignored} == {key: value for key, value in scoped.items() if key not in ignored}
    for key in ['released', 'original_key_verified', 'charging_worker_exited', 'no_concurrent_owner']:
        assert owner[key] is True
    assert owner['from_owner'] == 'charging' and owner['to_owner'] == 'camera'
    assert owner['boot_guard_path'] == handoff['boot_guard_path']
    assert owner['charging_manifest_sha256'] == handoff['charging']['manifest_sha256']


def gate(plan):
    authorization(plan, datetime.now(timezone.utc))
    handoff, owner = plan['handoff'], plan['owner']
    guard = Path(owner['boot_guard_path'])
    assert guard.is_absolute() and guard.is_file() and not guard.is_symlink()
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == owner['boot_id'] == guard.read_text().strip()
    assert os.uname().release == handoff['expected_uname']['release']
    assert os.uname().version == handoff['expected_uname']['version']
