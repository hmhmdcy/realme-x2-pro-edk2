"""Retain the first preflight failure, correct the actual IMX471 parameter."""
from pathlib import Path
import ast,json
R=Path(__file__).resolve().parent
failed=json.loads((R/'rear-raw-capture-validation.json').read_text())
assert failed['program_exit'] is None and failed['frames']==[] and failed['worker_exception'] and failed['camera_devices_suspended'] and failed['mclk1_mclk2_disabled']
source=(R/'native-capture.py').read_text()
assert source.count('experimental_full_resolution')==1
source=source.replace('experimental_full_resolution','unprocessed_fullres').replace('-{kind}-r1','-{kind}-r2')
source=source.replace('all_formats_restored=after_formats==saved_formats,media_graph_restored=media_after==media_before,sensor_controls_restored=control_match,',
 'all_formats_restored=bool(saved_formats) and after_formats==saved_formats,media_graph_restored=media_before is not None and media_after==media_before,sensor_controls_restored=bool(saved_controls) and control_match,')
source=source.replace('sensor_csid_patterns_zero=True,','sensor_csid_patterns_zero=bool(patterns) and all(v.get(\'test_pattern\')==0 for v in patterns.values()) and bool(saved_controls) and all(v.get(\'test_pattern\')==0 for v in saved_controls.values()),')
for name,text in [('native-capture-r2.py',source),('start-capture-r2.py',(R/'start-capture.py').read_text().replace('native-capture.py','native-capture-r2.py').replace('-{kind}-r1','-{kind}-r2').replace('rear-raw-capture-validation.json','rear-raw-capture-r2-validation.json')),('poll-capture-r2.py',(R/'poll-capture.py').read_text().replace('-{kind}-r1','-{kind}-r2').replace('-capture-validation.json','-capture-r2-validation.json')),('inspect-capture-r2-failure.py',(R/'inspect-capture-failure.py').read_text().replace('-{kind}-r1','-{kind}-r2').replace('-failure-details-private.json','-r2-failure-details-private.json'))]:
 ast.parse(text);p=R/name;assert not p.exists();p.write_text(text)
print(json.dumps(dict(stage=237,first_attempt_stopped_in_preflight_no_capture_process=True,actual_fullres_parameter_corrected=True,first_failure_and_source_preserved=True,new_capture_context_suffix='r2')))
