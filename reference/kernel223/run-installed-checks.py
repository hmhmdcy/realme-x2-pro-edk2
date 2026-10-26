"""Check the deployed libraries, gap metadata and dark-frame statistics."""
from pathlib import Path
import host,json

here=Path(__file__).resolve().parent
assert json.loads((here/'coherent-install-validation.json').read_text())['transaction_state']=='verified'
code=(here/'native-control-runner.py').read_text()
code=code.replace("tag=f'control-snapshot-", "tag=f'installed-control-snapshot-r2-")
code=code.replace("    candidate_libraries_verified=all(str(prefix/'usr/lib'/name) in maps for name in ['libcamera.so.0.7.2','libcamera-base.so.0.7.2'])", "    (out/'capture-maps-private.txt').write_text(maps)\n    library_maps='\\n'.join(l for l in maps.splitlines() if 'libcamera.so.' in l or 'libcamera-base.so.' in l)\n    installed_libraries_verified=all('/usr/lib/'+name in library_maps for name in ['libcamera.so.0.7.2','libcamera-base.so.0.7.2']) and '/run/samurai-camera' not in library_maps and '(deleted)' not in library_maps")
code=code.replace('candidate_libraries_verified=candidate_libraries_verified', 'installed_r8_libraries_verified=installed_libraries_verified')
code=code.replace('def demote():', "if profile=='isolated':env['XDG_CONFIG_HOME']='/run/samurai-camera223-r8/config-isolated'\ndef demote():")
failed=host.PRIVATE/'installed-1920x1088-threaded-host-private.log'
retained=host.PRIVATE/'installed-1920x1088-threaded-first-check-failed-private.log'
if failed.exists() and not retained.exists():
 retained.write_bytes(failed.read_bytes())
 (here/'installed-validator-correction.json').write_text(json.dumps(dict(stage=223,first_capture_completed_frames=16,first_capture_program_exit=0,
   validation_failure='Library path filter incorrectly included the test executable in /run.',
   correction='Filter only core and base camera library map lines; retain maps; fresh r2 case directory.',
   initial_report_retained_privately=True,first_capture_controls_formats_graph_pm_restored=True),indent=2)+'\n')
results=[]
for profile in ['threaded','isolated']:
 for width,height in [(1920,1088),(2296,1728)]:
  compile(code,'installed-control223','exec')
  p=host.ssh(f'python3 - rgb 0 {width} {height} 1 system {profile}',input=code.encode(),timeout=60)
  (host.PRIVATE/f'installed-{width}x{height}-{profile}-host-private.log').write_bytes(p.stdout+p.stderr)
  r=json.loads(p.stdout)
  assert r['program_exit']==0 and len(r['frames'])==16 and r['installed_r8_libraries_verified']
  assert r['all_formats_restored'] and r['media_graph_restored'] and r['sensor_controls_restored'] and r['camera_devices_suspended']
  assert r['taint']==0 and not any(r['fault_delta'].values())
  if profile=='isolated':assert r['ipa_isolation_forced_observed']
  # Read only numerical control log lines. Never fetch scene pixels.
  path=f'/var/lib/samurai/k223-capture-installed-control-snapshot-r2-rgb-{width}x{height}-{profile}/stderr-private.txt'
  reader="from pathlib import Path;import json,re;t=Path("+repr(path)+").read_text();print(json.dumps(dict(snapshots=re.findall(r'Captured request (\\d+) from sequence (\\d+), control sequence (\\d+)',t),exposure=re.findall(r'Reading Exposure to (\\d+) at index (\\d+)',t),gain=re.findall(r'Reading Analogue Gain to (\\d+) at index (\\d+)',t))))"
  parsed=json.loads(host.ssh('python3 -',input=reader.encode(),timeout=20).stdout)
  assert len(parsed['snapshots'])==len(parsed['exposure'])==len(parsed['gain'])==16
  sensor_width=1928 if width==1920 else 2304;c=r['active_controls'];line_us=(sensor_width+c['horizontal_blanking'])*1e6/c['pixel_rate'];errors=[]
  for frame,snapshot,exposure,gain in zip(r['frames'],parsed['snapshots'],parsed['exposure'],parsed['gain']):
   snapshot=tuple(map(int,snapshot));exposure=tuple(map(int,exposure));gain=tuple(map(int,gain))
   assert snapshot==(frame['request_sequence'],frame['buffer_sequence'],frame['buffer_sequence'])
   assert exposure[1]==gain[1]==max(0,frame['buffer_sequence']-2)
   errors.append(abs(frame['exposure_us']-exposure[0]*line_us))
   assert abs(frame['gain']-1024/(1024-gain[0]))<.0001
  assert max(errors)<1
  report=dict(stage=223,width=width,height=height,profile=profile,frames=16,installed_r8_libraries_verified=True,
              captured_sequences=[x['buffer_sequence'] for x in r['frames']],capture_control_history_association_verified=True,
              maximum_exposure_conversion_error_us=max(errors),gain_conversion_verified=True,ipa_forced_isolation_observed=r['ipa_isolation_forced_observed'],
              controls_formats_graph_and_pm_restored=True,taint=0,fault_delta=r['fault_delta'],no_client_pixel_mapping_or_scene_storage=True)
  (here/f'installed-controls-{width}x{height}-{profile}-validation.json').write_text(json.dumps(report,indent=2)+'\n')
  results.append(report);print(json.dumps(report),flush=True)
(here/'installed-control-validation.json').write_text(json.dumps(dict(stage=223,cases=results,frame_count=64,all_capture_control_associations_verified=True),indent=2)+'\n')

# Existing native probe maps only in RAM and reports aggregate statistics.
stats=(here.parent/'kernel219/native-mode-runner.py').read_text()
stats=stats.replace('k219-runtime/boot-id-private.txt','k223-baseline/boot-id-private.txt').replace("'k219-capture-'","'k223-capture-'")
stats=stats.replace("tag=f'{width}x{height}-{kind}-pattern{pattern}-{library}'", "tag=f'installed-dark-{kind}-{width}x{height}'")
stats=stats.replace('report=dict(stage=219,','report=dict(stage=223,')
for kind in ['raw','rgb']:
 p=host.ssh(f'python3 - {kind} 0 2304 1728 1 system' if kind=='raw' else 'python3 - rgb 0 2296 1728 1 system',input=stats.encode(),timeout=75)
 (host.PRIVATE/f'installed-dark-{kind}-host-private.log').write_bytes(p.stdout+p.stderr)
 r=json.loads(p.stdout);assert r['program_exit']==0 and len(r['frames'])==6
 assert r['all_formats_restored'] and r['media_graph_restored'] and r['sensor_controls_restored'] and r['camera_devices_suspended']
 assert r['taint']==0 and not any(r['fault_delta'].values())
 (here/f'installed-dark-{kind}-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
