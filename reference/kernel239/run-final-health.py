from pathlib import Path
import json
import host
R = Path(__file__).resolve().parent
for name in ['r15-startup-analysis.json', 'r15-installed-startup-analysis.json']:
    report = json.loads((R / name).read_text())
    assert report['initial_parameters_correct_on_both_starts']
    assert report['every_processing_identity_matches_callback_sequence_timestamp']
result = host.ssh('python3 -', input=(R / 'final-health.py').read_bytes(), timeout=110)
(host.PRIVATE / 'final-health-host-private.log').write_bytes(result.stdout + result.stderr)
report = json.loads(result.stdout)
(R / 'final-health-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
