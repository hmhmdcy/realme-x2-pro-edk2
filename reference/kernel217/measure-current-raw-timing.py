"""Measure hardware frame timestamps without saving images or changing mode tables."""
from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,os,pwd,re,signal,statistics,subprocess,time
os.umask(0o077);root=Path('/var/lib/samurai');base=root/'k217-baseline';assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(base/'boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
out=root/'k217-current-raw-timing';out.mkdir(mode=0o700)
nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='imx471 7-0010'];assert len(nodes)==1;sensor='/dev/'+nodes[0].name
names=['exposure','analogue_gain','digital_gain','vertical_blanking','test_pattern','horizontal_blanking','pixel_rate','link_frequency']
def controls():
    text=subprocess.check_output(['v4l2-ctl','-d',sensor,'--get-ctrl='+','.join(names)],text=True,timeout=10)
    return {k:int(v) for k,v in re.findall(r'(\w+):\s*(-?\d+)',text)}
saved=controls();assert saved['test_pattern']==0
user=pwd.getpwuid(10000);sessions=[]
for p in Path('/proc').iterdir():
    if not p.name.isdigit():continue
    try:
        if (p/'comm').read_text().strip()=='phosh' and int((p/'status').read_text().split('Uid:',1)[1].split()[0])==10000:sessions.append(p)
    except OSError:pass
assert len(sessions)==1;entries=dict(entry.split(b'=',1) for entry in (sessions[0]/'environ').read_bytes().split(b'\0') if b'=' in entry)
env=dict(PATH='/usr/bin:/bin',HOME=user.pw_dir,XDG_RUNTIME_DIR=entries[b'XDG_RUNTIME_DIR'].decode(),LIBCAMERA_LOG_LEVELS='*:INFO')
def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
p=subprocess.run(['cam','-l'],env=env,preexec_fn=demote,capture_output=True,text=True,timeout=15);assert p.returncode==0
ids=re.findall(r'^\d+: Internal front camera \((.+)\)$',p.stdout,re.M);assert len(ids)==1 and 'cci@ac4b000' in ids[0]
before=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(before)
try:
    p=subprocess.run(['cam','--camera',ids[0],'--stream=role=raw','--capture=12'],env=env,preexec_fn=demote,capture_output=True,text=True,timeout=20)
    (out/'stdout-private.txt').write_text(p.stdout);(out/'stderr-private.txt').write_text(p.stderr)
finally:
    for group in [['test_pattern','vertical_blanking'],['exposure','analogue_gain','digital_gain']]:subprocess.run(['v4l2-ctl','-d',sensor,'--set-ctrl='+','.join(key+'='+str(saved[key]) for key in group)],capture_output=True,check=True,timeout=10)
assert controls()==saved;assert p.returncode==0
time.sleep(2);after=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(after)
faults={key:after.count(value)-before.count(value) for key,value in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()};assert not any(faults.values())
frames=[dict(timestamp=float(match[1]),sequence=int(match[2])) for match in re.finditer(r'^(\d+\.\d+)\s+\([^\n]+?seq:\s*(\d+)',p.stdout,re.M)];assert len(frames)==12
intervals=[(b['timestamp']-a['timestamp'])/(b['sequence']-a['sequence']) for a,b in zip(frames,frames[1:])];assert all(value>0 for value in intervals)
reported_rate=saved['pixel_rate']/((1928+saved['horizontal_blanking'])*(1088+saved['vertical_blanking']))
report=dict(stage=217,physical_raw_frames=12,reported_pixel_rate=saved['pixel_rate'],line_length=1928+saved['horizontal_blanking'],frame_length=1088+saved['vertical_blanking'],fps_from_reported_controls=reported_rate,median_hardware_frame_interval_seconds=statistics.median(intervals),fps_from_hardware_timestamps=1/statistics.median(intervals),intervals_seconds=intervals,sequence_deltas=[b['sequence']-a['sequence'] for a,b in zip(frames,frames[1:])],controls_restored=True,scene_images_not_saved=True,external_illumination_used=False,camera_devices_suspended=all(Path(path,'power/runtime_status').read_text().strip()=='suspended' for path in ['/sys/bus/i2c/devices/7-0010','/sys/bus/platform/devices/acb3000.camss','/sys/bus/platform/devices/ac4b000.cci']),taint=int(Path('/proc/sys/kernel/tainted').read_text()),fault_delta=faults)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=80);(host.PRIVATE/'current-raw-timing-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'current-raw-timing-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
