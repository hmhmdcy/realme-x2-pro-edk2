"""Run one fresh native candidate case and verify capture-time control sources."""
from pathlib import Path
import host,json,re,sys

here=Path(__file__).resolve().parent
assert json.loads((here/'r13-staging-validation.json').read_text())['system_camera_packages_unchanged']
assert json.loads((here/'r13-agc-control-regression-validation.json').read_text())['passed']
assert len(sys.argv)==5;kind,width,height,profile=sys.argv[1:];width=int(width);height=int(height)
assert profile in ['threaded','isolated'] and (kind,width,height) in [('raw',1928,1088),('raw',2304,1728),('rgb',1920,1088),('rgb',2296,1728)]
label=f'r13-{kind}-{width}x{height}-{profile}'
p=host.ssh(f'python3 - {kind} 0 {width} {height} 1 candidate {profile}',input=(here/'native-r13-manual-runner.py').read_bytes(),timeout=140)
(host.PRIVATE/(label+'-manual-host-private.log')).write_bytes(p.stdout+p.stderr);r=json.loads(p.stdout)
(here/(label+'-manual-native-validation.json')).write_text(json.dumps(r,indent=2)+'\n')
assert r['program_exit']==0 and r['manual_test_passed'] and len(r['frames'])==128 and r['manual_phases']==9
assert r['candidate_libraries_verified'] and r['all_formats_restored'] and r['media_graph_restored'] and r['sensor_controls_restored'] and r['camera_devices_suspended']
assert r['taint']==0 and not any(r['fault_delta'].values())
if profile=='isolated':assert r['ipa_isolation_forced_observed']
path=f'/var/lib/samurai/k225-capture-manual-controls-r13-{kind}-{width}x{height}-{profile}/stderr-private.txt'
reader="from pathlib import Path;import json,re;t=Path("+repr(path)+").read_text();print(json.dumps(dict(snapshots=re.findall(r'Captured request (\\d+) from sequence (\\d+), control sequence (\\d+)',t),exposure=re.findall(r'Reading Exposure to (\\d+) at index (\\d+)',t),gain=re.findall(r'Reading Analogue Gain to (\\d+) at index (\\d+)',t),cookies=re.findall(r'Reading source cookie (\\d+) at index (\\d+)',t))))"
parsed=json.loads(host.ssh('python3 -',input=reader.encode(),timeout=25).stdout)
assert all(len(parsed[k])==128 for k in ['snapshots','exposure','gain','cookies'])
c=r['active_controls'];sensor_width=1928 if width in [1928,1920] else 2304;line_us=(sensor_width+c['horizontal_blanking'])*1e6/c['pixel_rate'];errors=[];different_request_and_captured_source=0
for frame,snapshot,exposure,gain,cookie in zip(r['frames'],parsed['snapshots'],parsed['exposure'],parsed['gain'],parsed['cookies']):
 snapshot=tuple(map(int,snapshot));exposure=tuple(map(int,exposure));gain=tuple(map(int,gain));cookie=tuple(map(int,cookie))
 assert snapshot==(frame['request_sequence'],frame['buffer_sequence'],frame['buffer_sequence'])
 assert exposure[1]==gain[1]==cookie[1]==max(0,frame['buffer_sequence']-2)
 errors.append(abs(frame['exposure_us']-exposure[0]*line_us))
 assert abs(frame['gain']-1024/(1024-gain[0]))<.0001
 assert frame['exposure_mode']==int(bool(cookie[0]&1)) and frame['gain_mode']==int(bool(cookie[0]&2))
 desired={0:3,1:3,2:3,3:0,4:3,5:2,6:1,7:3,8:0}[frame['phase']]
 different_request_and_captured_source+=cookie[0]!=desired
assert max(errors)<1
assert different_request_and_captured_source>0
sequences=[f['buffer_sequence'] for f in r['frames']]
assert max(sequences)>32 and any(b-a>1 for a,b in zip(sequences,sequences[1:]))
if kind=='raw':assert r['dma_exporters_observed']==['videobuf2_dma_sg']
report=dict(stage=225,candidate_framework='99990.7.2-r13',case=label,frames=128,phases=9,
 start_controls_applied_before_first_capture=True,independent_modes_ae_enable_priority_ignore_freeze_resume_restart_verified=True,
 captured_source_cookies_and_values_match_metadata=True,metadata_mode_differs_from_new_request_during_transition_frames=different_request_and_captured_source,
 source_cookies_survive_sof_gaps_and_ring_wrap=True,maximum_exposure_conversion_error_us=max(errors),
 gain_conversion_verified=True,ipa_isolation_forced_observed=r['ipa_isolation_forced_observed'],raw_only_no_rgb_dma_output=kind=='raw',
 controls_formats_graph_and_pm_restored=True,taint=0,fault_delta=r['fault_delta'],no_client_pixel_mapping_or_scene_storage=True,
 physical_optical_delay_not_calibrated=True,system_r11_r6_packages_unchanged=True)
(here/(label+'-manual-validation.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
