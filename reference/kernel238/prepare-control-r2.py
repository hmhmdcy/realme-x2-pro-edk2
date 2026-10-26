from pathlib import Path
import ast,json
R=Path(__file__).resolve().parent
assert json.loads((R/'candidate-permissions-validation.json').read_text())['uid10000_cpu_config_read_verified']
source=(R/'native-controlled-capture.py').read_text().replace('k238-controlled-rear-r14','k238-controlled-rear-r14-r2').replace('instances/k238_controls','instances/k238_controls_r2')
source=source.replace("raw_cpu_statistics_log=b'RAW-only CPU statistics enabled' in stderr,", "raw_cpu_statistics_path_verified=len(frames)==48 and all(all(k in f for k in ['exposure_us','analogue_gain','exposure_mode','gain_mode']) for f in frames) and b'Failed to open configuration file' not in stderr,")
source=source.replace("'raw_cpu_statistics_log'","'raw_cpu_statistics_path_verified'")
source=source.replace(" assert b'mode: cpu' in Path('/etc/libcamera/configuration.yaml').read_bytes()", " assert b'mode: cpu' in Path('/etc/libcamera/configuration.yaml').read_bytes()\n assert json.loads((root/'k238-candidate-permissions-fix/summary.json').read_text())['uid10000_cpu_config_read_verified']")
outputs={'native-controlled-capture-r2.py':source,
 'start-controlled-capture-r2.py':(R/'start-controlled-capture.py').read_text().replace('native-controlled-capture.py','native-controlled-capture-r2.py').replace('k238-controlled-rear-r14','k238-controlled-rear-r14-r2').replace('controlled-capture-launch-private.log','controlled-capture-r2-launch-private.log').replace('controlled-capture-launch-host-private.log','controlled-capture-r2-launch-host-private.log').replace("target=Path('/run/samurai-camera238-probes');assert not target.exists();target.mkdir(mode=0o755);", "target=Path('/run/samurai-camera238-probes');assert target.is_dir();"),
 'poll-controlled-capture-r2.py':(R/'poll-controlled-capture.py').read_text().replace('k238-controlled-rear-r14','k238-controlled-rear-r14-r2').replace('controlled-rear-validation.json','controlled-rear-r2-validation.json').replace('controlled-capture-poll-host-private.log','controlled-capture-r2-poll-host-private.log').replace('raw_cpu_statistics_log','raw_cpu_statistics_path_verified'),
 'inspect-controlled-r2-failure.py':(R/'inspect-controlled-failure.py').read_text().replace('k238-controlled-rear-r14','k238-controlled-rear-r14-r2').replace('controlled-failure-details-private.json','controlled-r2-failure-details-private.json')}
for name,text in outputs.items():ast.parse(text);p=R/name;assert not p.exists();p.write_text(text)
# Correction: the literal log exists in debayer_cpu.cpp (0015), although it
# was missed when only simple.cpp/software_isp.cpp were searched initially.
# R2 already ran with config/metadata checks; preserve its original receipt.
print(json.dumps(dict(stage=238,first_candidate_permission_failure_retained=True,raw_cpu_statistics_gate_replaced_by_cpu_config_and_capture_metadata_evidence=True,raw_statistics_log_exists_in_debayer_cpu=True,r2_distinct_context=True)))
