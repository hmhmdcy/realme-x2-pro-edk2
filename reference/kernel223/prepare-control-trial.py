"""Prepare a finite paired-kernel/r8 trial, preserving the existing system."""
from pathlib import Path
import json

here = Path(__file__).resolve().parent
assert json.loads((here/'r8-staging-validation.json').read_text())['system_camera_packages_unchanged']
runner = (here.parent/'kernel219/native-mode-runner.py').read_text()
runner = runner.replace('k219-runtime/boot-id-private.txt', 'k223-baseline/boot-id-private.txt')
runner = runner.replace("[(2304,1728,1)", "[(1920,1088,1),(1928,1088,1),(2304,1728,1)")
runner = runner.replace("tag=f'{width}x{height}-{kind}-pattern{pattern}-{library}'", "tag=f'control-snapshot-{kind}-{width}x{height}-{sys.argv[7]}'")
runner = runner.replace("kind,pattern,width,height,cell,library=sys.argv[1:]", "kind,pattern,width,height,cell,library=sys.argv[1:7]\nprofile=sys.argv[7];assert profile in ['threaded','isolated']")
runner = runner.replace("'k219-capture-'", "'k223-capture-'")
runner = runner.replace("LIBCAMERA_LOG_LEVELS='*:INFO'", "LIBCAMERA_LOG_LEVELS='*:INFO,DelayedControls:DEBUG,SimplePipeline:DEBUG,IPAManager:DEBUG'")
runner = runner.replace("names=['exposure','analogue_gain','digital_gain','vertical_blanking','test_pattern']", "names=['exposure','analogue_gain','digital_gain','vertical_blanking','test_pattern','horizontal_blanking','pixel_rate']")
runner = runner.replace("prefix=Path('/run/samurai-camera219-cpu')", "prefix=Path('/run/samurai-camera223-r8')")
runner = runner.replace("prefix/'config-enabled'", "prefix/('config-isolated' if profile=='isolated' else 'config-default')")
runner = runner.replace("LIBCAMERA_IPA_MODULE_PATH='/usr/lib/libcamera/ipa',LIBCAMERA_IPA_PROXY_PATH='/usr/libexec/libcamera',LIBCAMERA_IPA_CONFIG_PATH='/usr/share/libcamera/ipa'", "LIBCAMERA_IPA_MODULE_PATH=str(prefix/'usr/lib/libcamera/ipa'),LIBCAMERA_IPA_PROXY_PATH=str(prefix/'usr/libexec/libcamera'),LIBCAMERA_IPA_CONFIG_PATH=str(prefix/'usr/share/libcamera/ipa')")
old = "['/run/samurai-camera219-probes/native-mode-probe',sensor,kind,str(pattern),str(width),str(height),str(cell)]"
assert runner.count(old)==1
runner = runner.replace(old,"['/run/samurai-camera223-probes/paired-frame-probe',kind,str(width),str(height)]")
marker = '    try:stdout,stderr=process.communicate(timeout=25)'
assert runner.count(marker)==1
runner = runner.replace(marker, """    active_controls=controls()
    maps=Path('/proc',str(process.pid),'maps').read_text()
    candidate_libraries_verified=all(str(prefix/'usr/lib'/name) in maps for name in ['libcamera.so.0.7.2','libcamera-base.so.0.7.2'])
"""+marker)
runner = runner.replace('report=dict(stage=219,', "report=dict(stage=223,metadata_only=True,active_controls=active_controls,candidate_libraries_verified=candidate_libraries_verified,ipa_isolation_forced_observed=b'forced through configuration' in stderr,")
runner = runner.replace('dma_sync_read_start_end=True', 'dma_sync_read_start_end=False,no_client_pixel_buffer_access=True')
runner = runner.replace("all_active_raw_pixels_examined=kind=='raw'", 'all_active_raw_pixels_examined=False').replace("raw_padding_excluded=kind=='raw'", 'raw_padding_excluded=False')
compile(runner,'r8-control-runner223','exec')
(here/'native-control-runner.py').write_text(runner)

trial = (here/'native-paired-trial.py').read_text()
trial = trial.replace("out=root/'k223-paired-sof-trial'", "out=root/'k223-control-snapshot-trial'")
trial = trial.replace("for kind,width,height in [('raw',1928,1088),('rgb',1920,1088),('raw',2304,1728),('rgb',2296,1728)]:", "for kind,width,height,profile in [('raw',1928,1088,'threaded'),('raw',2304,1728,'threaded'),('rgb',1920,1088,'threaded'),('rgb',2296,1728,'threaded'),('rgb',1920,1088,'isolated'),('rgb',2296,1728,'isolated')]:")
trial = trial.replace("label=f'{kind}-{width}x{height}'", "label=f'{kind}-{width}x{height}-{profile}'")
trial = trial.replace("str(stage/'paired-runner.py'),kind,'0',str(width),str(height),'1','system'", "str(stage/'control-runner.py'),kind,'0',str(width),str(height),'1','candidate',profile")
trial = trial.replace("  assert not event_errors and events\n  tests.append", """  assert not event_errors and events
  assert test_data['candidate_libraries_verified'] and test_data['sensor_controls_restored']
  assert test_data['all_formats_restored'] and test_data['media_graph_restored'] and test_data['camera_devices_suspended']
  capture=root/f'k223-capture-control-snapshot-{kind}-{width}x{height}-{profile}'
  log=(capture/'stderr-private.txt').read_text()
  snapshots=[tuple(map(int,x)) for x in re.findall(r'Captured request (\\d+) from sequence (\\d+), control sequence (\\d+)',log)]
  exposure_reads=[tuple(map(int,x)) for x in re.findall(r'Reading Exposure to (\\d+) at index (\\d+)',log)]
  gain_reads=[tuple(map(int,x)) for x in re.findall(r'Reading Analogue Gain to (\\d+) at index (\\d+)',log)]
  checks=dict(capture_snapshots=len(snapshots),candidate_libraries_verified=True)
  if kind=='rgb':
   assert len(snapshots)==len(exposure_reads)==len(gain_reads)==16,(label,len(snapshots),len(exposure_reads),len(gain_reads))
   frames=test_data['frames'];sensor_width=1928 if width==1920 else 2304
   c=test_data['active_controls'];line_us=(sensor_width+c['horizontal_blanking'])*1000000/c['pixel_rate']
   exposure_errors=[];gain_errors=[]
   for frame,snapshot,exposure,gain in zip(frames,snapshots,exposure_reads,gain_reads):
    assert snapshot==(frame['request_sequence'],frame['buffer_sequence'],frame['buffer_sequence'])
    assert exposure[1]==gain[1]==max(0,frame['buffer_sequence']-2)
    exposure_errors.append(abs(frame['exposure_us']-exposure[0]*line_us))
    gain_errors.append(abs(frame['gain']-1024/(1024-gain[0])))
   assert max(exposure_errors)<1 and max(gain_errors)<0.0001
   assert profile!='isolated' or test_data['ipa_isolation_forced_observed']
   checks.update(all_capture_and_control_sequences_equal=True,all_delayed_history_indices_follow_capture_not_request=True,
                 exposure_metadata_conversion_error_us=max(exposure_errors),gain_metadata_conversion_error=max(gain_errors),
                 sensor_line_duration_us=line_us,forced_ipa_isolation_verified=profile=='isolated')
  tests.append""")
trial = trial.replace("client_exit=test_data['program_exit']))", "client_exit=test_data['program_exit'],control_checks=checks))")
trial = trial.replace("case=case['case'],capture_frames=len(frames)", "case=case['case'],control_checks=case['control_checks'],capture_frames=len(frames)")
trial = trial.replace('assert len(cases)==4', 'assert len(cases)==6')
trial = trial.replace('manual_api_and_control_snapshots_not_yet_accepted=True', 'capture_time_control_snapshots_verified=True,manual_api_not_yet_implemented=True,physical_optical_delay_not_calibrated=True,system_r7_packages_unchanged=True')
compile(trial,'r8-control-trial223','exec')
(here/'native-control-trial.py').write_text(trial)

wrapper = '''from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
runner=(here/'native-control-runner.py').read_bytes()
code="from pathlib import Path;p=Path('/var/lib/samurai/k223-sof-modules/control-runner.py');assert not p.exists();p.write_bytes("+repr(runner)+")"
host.ssh('python3 -',input=code.encode(),timeout=25)
p=host.ssh('python3 -',input=(here/'native-control-trial.py').read_bytes(),timeout=210)
(host.PRIVATE/'control-trial-host-private.log').write_bytes(p.stdout+p.stderr)
r=json.loads(p.stdout);(here/'control-snapshot-native-validation.json').write_text(json.dumps(r,indent=2)+'\\n');print(json.dumps(r))
'''
compile(wrapper,'run-r8-control-trial223','exec')
(here/'run-control-trial.py').write_text(wrapper)
print('K223_R8_CONTROL_SNAPSHOT_TRIAL_PREPARED')
