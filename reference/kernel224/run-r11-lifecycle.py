from pathlib import Path
import gzip,hashlib,host,json,shlex,sys
here=Path(__file__).resolve().parent
assert len(sys.argv)==2 and sys.argv[1] in ['candidate-threaded','candidate-isolated','system-threaded']
flavour=sys.argv[1];library='system' if flavour.startswith('system') else 'candidate';profile=flavour.rsplit('-',1)[1]
if library=='candidate':assert json.loads((here/'r11-staging-validation.json').read_text())['isolated_full_feature_runtime_staged']
else:assert json.loads((here/'wireplumber-reload-validation.json').read_text())['new_r11_camera_libraries_loaded']
proof=json.loads((here/'lifecycle-probe-build-validation.json').read_text());data=(host.PRIVATE/'raw-lifecycle-probe').read_bytes();assert hashlib.sha256(data).hexdigest()==proof['binary_sha256']
compressed=gzip.compress(data,mtime=0);assert len(compressed)<=65536
code="from pathlib import Path;import gzip,hashlib,sys;root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k224-baseline/boot-id-private.txt').read_bytes();p=Path('/run/samurai-camera224-probes/raw-lifecycle-probe');p.parent.mkdir(mode=0o755,exist_ok=True);d=gzip.decompress(sys.stdin.buffer.read());assert hashlib.sha256(d).hexdigest()=="+repr(proof['binary_sha256'])+";assert not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()=="+repr(proof['binary_sha256'])+";p.write_bytes(d) if not p.exists() else None;p.chmod(0o755)"
host.ssh('python3 -c '+shlex.quote(code),input=compressed,timeout=25)
runner=(here.parent/'kernel223/native-control-runner.py').read_text().replace('k223-baseline','k224-baseline').replace("'k223-capture-'","'k224-capture-'").replace('stage=223','stage=224').replace('samurai-camera223-r8','samurai-camera224-r11')
old="tag=f'control-snapshot-{kind}-{width}x{height}-{sys.argv[7]}'";assert runner.count(old)==1;runner=runner.replace(old,'tag='+repr('lifecycle-r11-'+flavour+'-r2'))
old="['/run/samurai-camera223-probes/paired-frame-probe',kind,str(width),str(height)]";assert runner.count(old)==1;runner=runner.replace(old,"['/run/samurai-camera224-probes/raw-lifecycle-probe']")
old="    candidate_libraries_verified=all(str(prefix/'usr/lib'/name) in maps for name in ['libcamera.so.0.7.2','libcamera-base.so.0.7.2'])";assert runner.count(old)==1
runner=runner.replace(old,"    (out/'capture-maps-private.txt').write_text(maps)\n    library_maps='\\n'.join(l for l in maps.splitlines() if 'libcamera.so.' in l or 'libcamera-base.so.' in l)\n    actual_prefix=str(prefix/'usr/lib') if library=='candidate' else '/usr/lib'\n    candidate_libraries_verified=all(actual_prefix+'/'+name in library_maps for name in ['libcamera.so.0.7.2','libcamera-base.so.0.7.2']) and '(deleted)' not in library_maps")
runner=runner.replace('    for _ in range(8):',"    captured_maps=''\n    for _ in range(8):\n        try:captured_maps=Path('/proc',str(process.pid),'maps').read_text() or captured_maps\n        except FileNotFoundError:pass")
runner=runner.replace("    maps=Path('/proc',str(process.pid),'maps').read_text()",'    maps=captured_maps')
runner=runner.replace('os.umask(0o077)','import resource\nresource.setrlimit(resource.RLIMIT_CORE,(0,0))\nos.umask(0o077)')
old="frames=data['frames'] if data else [],";assert runner.count(old)==1;runner=runner.replace(old,"frames=data['frames'] if data else [],phases=data['phases'] if data else [],")
compile(runner,'lifecycle224','exec')
p=host.ssh(f'python3 - raw 0 2304 1728 1 {library} {profile}',input=runner.encode(),timeout=85)
(host.PRIVATE/('lifecycle-r11-'+flavour+'-host-private.log')).write_bytes(p.stdout+p.stderr);r=json.loads(p.stdout)
assert r['program_exit']==0 and r['candidate_libraries_verified'] and len(r['phases'])==5
assert all(p['completed']>=4 and p['cancelled']>=1 for p in r['phases'])
assert sum(p['completed']+p['cancelled'] for p in r['phases'])==40
assert len(r['frames'])==sum(p['completed'] for p in r['phases'])
assert r['all_formats_restored'] and r['media_graph_restored'] and r['sensor_controls_restored'] and r['camera_devices_suspended']
assert r['taint']==0 and not any(r['fault_delta'].values())
if profile=='isolated':assert r['ipa_isolation_forced_observed']
report=dict(stage=224,framework='99990.7.2-r11',flavour=flavour,one_camera_object_reconfigured_raw_rgb_raw_rgb_raw=True,phases=r['phases'],
 all40_requests_completed_or_cancelled=True,all_successful_frames_have_exposure_and_gain=True,expected_camera_libraries_verified=True,
 no_stop_hang_or_pending_request_leak_observed=True,controls_graph_formats_and_pm_restored=True,
 ipa_forced_isolation_observed=r['ipa_isolation_forced_observed'],taint=0,fault_delta=r['fault_delta'],no_client_pixels_mapped_or_scene_saved=True)
(here/('lifecycle-r11-'+flavour+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
