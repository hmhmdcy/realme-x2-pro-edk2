"""Verify the real two-message sensor ID reply; publish only the chip model."""
from pathlib import Path
import json
import re
import host

R = Path(__file__).resolve().parent
code = r'''
from pathlib import Path
import json
root=Path('/var/lib/samurai');out=root/'k236-lab-fix'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k236-runtime/boot-id-private.txt').read_bytes()
state=json.loads((out/'state-private.json').read_text())
assert state['state']=='terminal' and state['exit_code']==0
print(json.dumps(dict(trace=(out/'i2c-trace-private.txt').read_text(),stats=json.loads((out/'trace-stats-private.json').read_text()),
                     summary=json.loads((out/'summary.json').read_text()))))
'''
result = host.ssh('python3 -', input=code.encode(), timeout=20)
(host.PRIVATE / 'id-trace-bundle-private.json').write_bytes(result.stdout)
bundle = json.loads(result.stdout)
lines = [line for line in bundle['trace'].splitlines() if not line.startswith('#') and line.strip()]
assert len(lines) == 3, 'Unexpected number of sensor-ID trace entries; inspect saved trace'
patterns = [r'i2c_write: i2c-7 #0 a=010 f=0000 l=2 \[00-16\]',
            r'i2c_read: i2c-7 #1 a=010 f=0001 l=2',
            r'i2c_reply: i2c-7 #1 a=010 f=0001 l=2 \[03-19\]']
assert all(re.search(pattern, line) for pattern, line in zip(patterns, lines))
loss = {}
for cpu, text in bundle['stats'].items():
    for key in ['overrun', 'commit overrun', 'dropped events']:
        found = re.search(r'^' + key + r':\s*(\d+)\s*$', text, re.M)
        assert found, (cpu, key)
        loss[cpu + ':' + key] = int(found[1])
assert not any(loss.values())
assert bundle['summary']['trace_instance_removed'] and bundle['summary']['taint'] == 0
assert not any(bundle['summary']['fault_counts'].values())
report = dict(stage=236, actual_chip_id='0x0319', actual_register='0x0016',
              actual_i2c_write_address_read_and_completed_reply=True, trace_entries=3,
              only_sensor_adapter_and_address_filtered=True, no_pid_filter=True,
              trace_loss_counters_zero=True, trace_instance_removed=True,
              rear_probe_and_autosuspend_passed=True, no_scene_pixels=True,
              capture_not_yet_tested=True, first_failed_observer_preserved=True)
(R / 'id-trace-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
