"""Prepare a current-state health check and a private archive of this turn."""
from pathlib import Path
import ast,json
R=Path(__file__).resolve().parent
for which,kind in [('rear','raw'),('front','raw'),('front','rgb')]:assert json.loads((R/f'{which}-{kind}-capture-r2-validation.json').read_text())['passed']
health=(R.parent/'kernel236/final-health.py').read_text()
health=health.replace('Current236 health with the corrected lab and both real sensor drivers.','Current237 CAMSS unwind plus rear RAW and front RAW/RGB health.')
health=health.replace("out = root / 'k236-final-health-r2'","out = root / 'k237-final-health'")
health=health.replace("root / 'k236-lab-fix/module-inventory-after-private.json'","root / 'k237-camss-install/module-inventory-after-private.json'")
health=health.replace('report = dict(stage=236,','report = dict(stage=237,')
health=health.replace('no_scene_capture=True)','no_scene_pixels_saved=True, rear_raw_six_frames=True, front_raw_rgb_six_each=True)')
prefix="for which, kind in [('rear','raw'),('front','raw'),('front','rgb')]:\n    assert json.loads((root / f'k237-capture-{which}-{kind}-r2/summary.json').read_text())['passed']\n"
health=health.replace("tree = Path('/usr/lib/modules')",prefix+"\ntree = Path('/usr/lib/modules')")
(R/'final-health.py').write_text(health)
run=(R.parent/'kernel236/run-final-health.py').read_text();(R/'run-final-health.py').write_text(run)
evidence=(R.parent/'kernel236/export-evidence.py').read_text()
a=evidence.index("assert json.loads((root/'k236-runtime/state-private.json')");b=evidence.index('files=[]',a)
evidence=evidence[:a]+'''assert json.loads((root/'k237-camss-install/state-private.json').read_text())['exit_code']==0
assert json.loads((root/'k237-final-health/summary.json').read_text())['taint']==0
names=['k237-baseline','k237-tools','k237-camss-install','k237-capture-rear-raw-r1',
       'k237-capture-rear-raw-r2','k237-capture-front-raw-r2','k237-capture-front-rgb-r2','k237-final-health']
'''+evidence[b:]
evidence=evidence.replace('k236-evidence','k237-evidence').replace('stage=236','stage=237')
evidence=evidence.replace('transition_failed_first_probe_fixed_lab_id_trace_and_health_preserved=True,','camss_swap_rear_six_raw_front_six_raw_six_rgb_and_health_preserved=True,')
evidence=evidence.replace('first_observer_failure_and_first_health_assumption_failure_retained=True,','first_preflight_parameter_failure_retained=True,')
(R/'export-evidence.py').write_text(evidence)
for name in ['final-health.py','run-final-health.py','export-evidence.py']:ast.parse((R/name).read_text())
rear=json.loads((R/'rear-raw-capture-r2-validation.json').read_text());frames=rear['frames']
times=[f['timestamp_ns'] for f in frames];deltas=[b-a for a,b in zip(times,times[1:])];sequences=[f['sequence'] for f in frames]
assert sequences==list(range(6))
report=dict(stage=237,rear_physical_raw_frames=6,dimensions=rear['requested'],stride=rear['stream_geometry']['stride'],active_raw10_bytes_per_row=2040,row_padding_bytes=8,
 sequences=sequences,completion_period_ms_range=[min(deltas)/1e6,max(deltas)/1e6],completion_observed_fps=5e9/(times[-1]-times[0]),
 raw10_sample_min=min(f['byte_min'] for f in frames),raw10_sample_max=max(f['byte_max'] for f in frames),mean_range=[min(f['mean'] for f in frames),max(f['mean'] for f in frames)],
 changed_fraction_range=[min(f['changed_fraction'] for f in frames[1:]),max(f['changed_fraction'] for f in frames[1:])],
 not_all_zero=True,near_black_level64=True,optical_response_and_colour_not_yet_verified=True,completion_cadence_not_exposure_calibration=True,front_raw_rgb_regression_passed=True)
(R/'capture-analysis.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
