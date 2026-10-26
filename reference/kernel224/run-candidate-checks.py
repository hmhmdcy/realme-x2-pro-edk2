"""Finite RAW/RGB metadata checks in threaded and isolated IPA modes."""
from pathlib import Path
import host,json,re

here=Path(__file__).resolve().parent
assert json.loads((here/'r9-staging-validation.json').read_text())['system_camera_packages_unchanged']
runner=(here.parent/'kernel223/native-control-runner.py').read_text()
runner=runner.replace('k223-baseline','k224-baseline').replace("'k223-capture-'","'k224-capture-'").replace('stage=223','stage=224')
runner=runner.replace('samurai-camera223-r8','samurai-camera224-r9').replace("tag=f'control-snapshot-","tag=f'r9-raw-statistics-")
compile(runner,'candidate-raw-statistics224','exec')
results=[]
for profile in ['threaded','isolated']:
 for kind,width,height in [('raw',1928,1088),('raw',2304,1728),('rgb',1920,1088),('rgb',2296,1728)]:
  label=f'{kind}-{width}x{height}-{profile}'
  p=host.ssh(f'python3 - {kind} 0 {width} {height} 1 candidate {profile}',input=runner.encode(),timeout=70)
  (host.PRIVATE/(label+'-candidate-host-private.log')).write_bytes(p.stdout+p.stderr)
  r=json.loads(p.stdout)
  assert r['program_exit']==0 and len(r['frames'])==16 and r['candidate_libraries_verified']
  assert r['all_formats_restored'] and r['media_graph_restored'] and r['sensor_controls_restored'] and r['camera_devices_suspended']
  assert r['taint']==0 and not any(r['fault_delta'].values())
  if profile=='isolated':assert r['ipa_isolation_forced_observed']
  path=f'/var/lib/samurai/k224-capture-r9-raw-statistics-{kind}-{width}x{height}-{profile}/stderr-private.txt'
  reader="from pathlib import Path;import json,re;t=Path("+repr(path)+").read_text();print(json.dumps(dict(snapshots=re.findall(r'Captured request (\\d+) from sequence (\\d+), control sequence (\\d+)',t),exposure=re.findall(r'Reading Exposure to (\\d+) at index (\\d+)',t),gain=re.findall(r'Reading Analogue Gain to (\\d+) at index (\\d+)',t),stats_only='RAW-only CPU statistics enabled' in t,sensor_updates=len(re.findall(r'Setting (?:Exposure|Analogue Gain) to',t)))))"
  parsed=json.loads(host.ssh('python3 -',input=reader.encode(),timeout=20).stdout)
  assert len(parsed['snapshots'])==len(parsed['exposure'])==len(parsed['gain'])==16
  assert parsed['stats_only']==(kind=='raw')
  sensor_width=1928 if width in [1920,1928] else 2304;c=r['active_controls'];line_us=(sensor_width+c['horizontal_blanking'])*1e6/c['pixel_rate'];errors=[]
  for frame,snapshot,exposure,gain in zip(r['frames'],parsed['snapshots'],parsed['exposure'],parsed['gain']):
   snapshot=tuple(map(int,snapshot));exposure=tuple(map(int,exposure));gain=tuple(map(int,gain))
   assert frame['exposure_us']>0 and 1<=frame['gain']<=16
   assert snapshot==(frame['request_sequence'],frame['buffer_sequence'],frame['buffer_sequence'])
   assert exposure[1]==gain[1]==max(0,frame['buffer_sequence']-2)
   errors.append(abs(frame['exposure_us']-exposure[0]*line_us))
   assert abs(frame['gain']-1024/(1024-gain[0]))<.0001
  assert max(errors)<1
  changed=len({(f['exposure_us'],f['gain']) for f in r['frames']})>1
  if kind=='raw':
   assert changed and parsed['sensor_updates']>0
   assert r['dma_exporters_observed']==['videobuf2_dma_sg'],r['dma_exporters_observed']
  report=dict(stage=224,case=label,frames=16,candidate_libraries_verified=True,raw_only_cpu_statistics=parsed['stats_only'],
              original_raw_buffers_and_no_rgb_dma_outputs_verified=kind=='raw',capture_control_association_verified=True,
              capture_sequences=[f['buffer_sequence'] for f in r['frames']],exposure_metadata_microseconds=[f['exposure_us'] for f in r['frames']],
              gain_metadata=[f['gain'] for f in r['frames']],maximum_exposure_conversion_error_us=max(errors),gain_conversion_verified=True,
              automatic_exposure_or_gain_updates_observed=changed,sensor_update_log_entries=parsed['sensor_updates'],
              ipa_forced_isolation_observed=r['ipa_isolation_forced_observed'],controls_graph_formats_and_pm_restored=True,
              taint=0,fault_delta=r['fault_delta'],no_client_pixel_mapping_or_scene_storage=True,manual_api_not_yet_implemented=True)
  (here/(label+'-candidate-validation.json')).write_text(json.dumps(report,indent=2)+'\n');results.append(report)
  print(json.dumps({k:v for k,v in report.items() if k not in ['capture_sequences','exposure_metadata_microseconds','gain_metadata']}),flush=True)
(here/'candidate-native-validation.json').write_text(json.dumps(dict(stage=224,cases=results,capture_frames=128,raw_frames=64,
 raw_only_exposure_gain_metadata_and_automatic_updates_verified=True,rgb_regression_verified=True,
 no_rgb_dma_outputs_for_raw=True,threaded_and_isolated_ipa_verified=True,system_r8_packages_unchanged=True),indent=2)+'\n')
