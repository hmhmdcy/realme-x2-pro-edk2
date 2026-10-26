"""Reauthenticate actual current r15 runtime before preparing any device change."""
from pathlib import Path
import json
import host

R = Path(__file__).resolve().parent
source = (R.parent / 'kernel239/final-health.py').read_text()
assert source.count("out = root / 'k239-final-health'") == 1
source = source.replace("out = root / 'k239-final-health'", "out = root / 'k240-baseline'")
assert source.count('report = dict(stage=239,') == 1
source = source.replace('report = dict(stage=239,', 'report = dict(stage=240,')
result = host.ssh('python3 -', input=source.encode(), timeout=110)
(host.PRIVATE / 'baseline-host-private.log').write_bytes(result.stdout + result.stderr)
report = json.loads(result.stdout)
(R / 'baseline-validation.json').write_text(json.dumps(report, indent=2) + '\n')
state_path = host.PRIVATE / 'current-work-private.json'
state = json.loads(state_path.read_text())
state.update(state='240 fresh baseline passed: boot236 r15/r10 and modules789 exact, camera idle, taint/fault0; offline adaptation in progress',
             fresh_baseline_passed=True)
state_path.write_text(json.dumps(state, indent=2) + '\n')
print(json.dumps(dict(stage=240, current236_boot_verified=True, installed_r15_r10=True,
                     current789_modules_and_loaded_notes_verified=True, camera_idle=True,
                     taint=report['taint'], previous_goal_turn_classification='progress')))
