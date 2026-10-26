"""Observe normal recharge after recovery. Never changes any device control."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', required=True)
    parser.add_argument('--directory', required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if not args.execute:
        parser.error('observation requires --execute')
    baseline = json.loads(Path(args.baseline).read_bytes())
    assert baseline['passed'] and os.geteuid() == 0
    expected = baseline['boot_id']
    bootfile = Path('/proc/sys/kernel/random/boot_id')
    assert bootfile.read_text().strip() == expected
    assert Path(baseline['guard_path']).read_text().strip() == expected
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    assert sha('/usr/share/samurai-charging/manifest.json') == baseline['manifest_sha256']
    assert os.uname().version == '#506 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
    for name, digest in baseline['notes'].items():
        assert sha('/sys/module/' + name + '/notes/.note.gnu.build-id') == digest
    root = Path(args.directory)
    assert root.is_dir() and not (root / 'observer-began.json').exists()
    start = time.clock_gettime(time.CLOCK_BOOTTIME)
    (root / 'observer-began.json').write_text(json.dumps(dict(boot=expected, boottime=start)) + '\n')
    result = dict(ready_for_fresh_preflight=False, device_controls_changed=False,
                  physical_usb_tested=False, flash_started=False, error=None)
    consecutive = 0
    count = 0
    try:
        with (root / 'samples-private.jsonl').open('x') as log:
            while True:
                assert bootfile.read_text().strip() == expected
                now = time.clock_gettime(time.CLOCK_BOOTTIME)
                if now - start >= 21600:
                    result['reason'] = 'six_hour_observation_deadline'
                    break
                raw = Path('/sys/bus/i2c/devices/0-005c/telemetry').read_text()
                sample = {k: int(v) for k, v in (word.split('=') for word in raw.split())}
                psy = Path('/sys/class/power_supply')
                capacity = int((psy / 'bq28z610-0/capacity').read_text())
                mode = (psy / 'mp2650-input/charge_behaviour').read_text().strip()
                assert sample['valid'] == sample['online'] == sample['protection_ok'] == 1
                assert sample['shadow'] == 0 and 0 <= sample['age_ms'] <= 3000
                assert not any(sample[k] for k in ['fault', 'error', 'stop_error', 'latched',
                    'cycle_timeout', 'thermal_inhibit', 'source_inhibit', 'gauge_charge_stop'])
                assert '[auto]' in mode and 180 <= sample['temp_decic'] < 400
                assert 3200000 <= min(sample['cell1_uv'], sample['cell2_uv'])
                assert max(sample['cell1_uv'], sample['cell2_uv']) <= 4375000
                assert sample['budget_ua'] == 500000
                assert abs(sample['cell1_uv'] - sample['cell2_uv']) <= 30000
                row = dict(boottime=now, capacity=capacity, behaviour=mode, sample=sample)
                log.write(json.dumps(row) + '\n'); log.flush()
                count += 1
                result['last'] = row
                ready = capacity >= 20 and min(sample['cell1_uv'], sample['cell2_uv']) >= 3700000
                consecutive = consecutive + 1 if ready else 0
                if consecutive >= 2:
                    result.update(ready_for_fresh_preflight=True, reason='normal_recharge_reserve_observed')
                    break
                time.sleep(30)
    except BaseException as error:
        result.update(error=repr(error), reason='observation_interrupted_or_health_gate')
    result.update(records=count, boot=expected, elapsed_seconds=time.clock_gettime(time.CLOCK_BOOTTIME)-start)
    (root / 'result-private.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return 0 if result['error'] is None else 1


if __name__ == '__main__':
    raise SystemExit(main())
