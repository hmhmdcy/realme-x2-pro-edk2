"""Permit only the freshly identified idle policy observer; retain first failure."""
from pathlib import Path
import ast
import json

R=Path(__file__).resolve().parent
first=json.loads((R/'upright-validation.json').read_text())
assert first['worker_exception'] and not first['frames'] and first['program_exit'] is None
assert not first['restore_errors'] and not any(first['fault_delta'].values())
native=(R/'native-upright.py').read_text().replace('k240-upright-paired-r15','k240-upright-paired-r15-r2')
anchor=" for proc in Path('/proc').glob('[0-9]*'):"
assert native.count(anchor)==1
native=native.replace(anchor," policy=json.loads((root/'k240-tools/idle-policy-identity-private.json').read_text())\n"+anchor)
old="   assert not path.startswith(('/dev/video','/dev/v4l-subdev','/dev/media')),'other camera client'"
assert native.count(old)==1
native=native.replace(old,"""   if path.startswith(('/dev/video','/dev/v4l-subdev','/dev/media')):
    assert int(proc.name)==policy['pid'] and (proc/'stat').read_text().rsplit(')',1)[1].split()[19]==policy['start_ticks'],'other camera client'
    assert (proc/'comm').read_text().strip()=='wireplumber' and os.readlink(proc/'exe')=='/usr/bin/wireplumber'
    assert int((proc/'status').read_text().split('Uid:',1)[1].split()[0])==10000
    assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in devices),'policy observer is no longer idle'""")
native=native.replace('paired_same_request=True,','paired_same_request=True,idle_policy_observer_allowed_by_exact_process_identity=True,')
ast.parse(native);(R/'native-upright-r2.py').write_text(native)
start=(R/'start-upright.py').read_text().replace("native-upright.py","native-upright-r2.py").replace('k240-upright-paired-r15','k240-upright-paired-r15-r2')
start=start.replace('host.ssh("mkdir -m 700 /var/lib/samurai/k240-tools", timeout=10)\n','')
anchor="assert not (r/'k240-upright-paired-r15-r2').exists()"
assert start.count(anchor)==1
start=start.replace(anchor,anchor+"""
assert json.loads((r/'k240-upright-paired-r15/state-private.json').read_text())['state']=='terminal'
old=json.loads((r/'k240-upright-paired-r15/summary.json').read_text());assert not old['frames'] and old['worker_exception'] and not old['restore_errors']
assert b'other camera client' in (r/'k240-upright-paired-r15/failure-private.txt').read_bytes()
policies=[]
for proc in Path('/proc').glob('[0-9]*'):
 try:
  if (proc/'comm').read_text().strip()=='wireplumber' and int((proc/'status').read_text().split('Uid:',1)[1].split()[0])==10000:
   assert os.readlink(proc/'exe')=='/usr/bin/wireplumber'
   policies.append(dict(pid=int(proc.name),start_ticks=(proc/'stat').read_text().rsplit(')',1)[1].split()[19]))
 except OSError:pass
assert len(policies)==1
assert all(Path('/sys/bus/i2c/devices',node,'power/runtime_status').read_text().strip()=='suspended' for node in ['7-0010','9-0010'])
(r/'k240-tools/idle-policy-identity-private.json').write_text(json.dumps(policies[0],indent=2)+'\\n')
""")
start=start.replace("assert not target.exists();target.mkdir(mode=0o755)","assert target.is_dir() and (target/'upright-paired-probe240').is_file()")
start=start.replace("with (r/'k240-tools/upright-launch-private.log').open('xb')", "with (r/'k240-tools/upright-r2-launch-private.log').open('xb')")
start=start.replace("'upright-launch-host-private.log'", "'upright-r2-launch-host-private.log'")
ast.parse(start);(R/'start-upright-r2.py').write_text(start)
poll=(R/'poll-upright.py').read_text().replace('k240-upright-paired-r15','k240-upright-paired-r15-r2').replace('upright-poll-host-private','upright-r2-poll-host-private').replace('upright-validation.json','upright-r2-validation.json').replace('upright-parameter-log-lines-private','upright-r2-parameter-log-lines-private')
ast.parse(poll);(R/'poll-upright-r2.py').write_text(poll)
report=dict(stage=240,first_attempt_stopped_before_capture=True,first_attempt_frames=0,
    cause='An idle WirePlumber CameraManager retained media/subdevice/video descriptors; no sensor stream was active.',
    first_failure_and_complete_cleanup_preserved=True,r2_allows_only_fresh_exact_idle_policy_process=True,
    real_libcamera_media_exclusive_acquisition_still_required=True,no_policy_process_stopped=True)
(R/'upright-first-failure-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('Upright r2 prepared after inspecting the actual first failure; media acquire remains exclusive')
