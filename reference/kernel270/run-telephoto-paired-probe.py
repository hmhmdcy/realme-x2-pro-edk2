"""Run the verified probe under the normal user and report only RAM statistics."""
from pathlib import Path
import base64,hashlib,json,shlex,sys
import host
R=Path(__file__).resolve().parent;proof=json.loads((R/'paired-probe-build-validation.json').read_text())
binary=(host.PRIVATE/'telephoto-paired-probe270').read_bytes();assert hashlib.sha256(binary).hexdigest()==proof['binary_sha256']
resume=sys.argv[1:]==['--resume-upload'];assert not sys.argv[1:] or resume
if resume:
 seen=json.loads((host.PRIVATE/'paired-upload-inspection-private.json').read_text())
 assert not seen['capture_context_exists'] and isinstance(seen['bytes'],int) and 0<=seen['bytes']<=len(binary)
 assert hashlib.sha256(binary[:seen['bytes']]).hexdigest()==seen['sha256']
 offset_start=seen['bytes']
else:
 setup="from pathlib import Path;import os;os.umask(0o077);p=Path('/run/samurai-camera270-probes');p.mkdir(mode=0o755);p.chmod(0o755);(p/'telephoto-paired-probe270').write_bytes(b'')"
 host.ssh('python3 -c '+shlex.quote(setup),timeout=15);offset_start=0
for offset in range(offset_start,len(binary),24576):
 chunk=binary[offset:offset+24576]
 code="from pathlib import Path;import sys;p=Path('/run/samurai-camera270-probes/telephoto-paired-probe270');assert p.stat().st_size=="+str(offset)+";f=p.open('ab');f.write(sys.stdin.buffer.read());f.close()"
 host.ssh('python3 -c '+shlex.quote(code),input=chunk,timeout=15)
check="from pathlib import Path;import hashlib;p=Path('/run/samurai-camera270-probes/telephoto-paired-probe270');assert hashlib.sha256(p.read_bytes()).hexdigest()=="+repr(proof['binary_sha256'])+";p.chmod(0o755)"
host.ssh('python3 -c '+shlex.quote(check),timeout=15)
code=r'''
from pathlib import Path
import hashlib,json,os,pwd,re,statistics,subprocess,time,traceback
os.umask(0o077);root=Path('/var/lib/samurai/k270-telephoto-paired-r1');root.mkdir(mode=0o700)
state=dict(state='preflight',terminal=False,pid=os.getpid());(root/'state-private.json').write_text(json.dumps(state))
u=pwd.getpwuid(10000)
def demote():os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid)
env=dict(PATH='/usr/bin:/bin',HOME=u.pw_dir,LIBCAMERA_LOG_LEVELS='*:INFO,SimplePipeline:DEBUG,Debayer:DEBUG,IPASoftBL:DEBUG')
node=next('/dev/'+p.name for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='s5k3m5 8-002d')
assert Path('/sys/bus/i2c/devices/8-002d/power/runtime_status').read_text().strip()=='suspended'
assert 'test_pattern: 0' in subprocess.check_output(['v4l2-ctl','-d',node,'--get-ctrl=test_pattern'],text=True)
before=subprocess.check_output(['dmesg'])
q=subprocess.run(['/run/samurai-camera270-probes/telephoto-paired-probe270',node,'/base/soc@0/cci@ac4b000/i2c-bus@0/camera@2d','s5k3m5','s5k3m5 8-002d','rgb','2048','1536','1'],env=env,preexec_fn=demote,capture_output=True,timeout=60)
(root/'stdout-private.json').write_bytes(q.stdout);(root/'stderr-private.log').write_bytes(q.stderr)
frames=json.loads(q.stdout)['frames'] if q.stdout else [];phases=[]
for index,exposure in [(0,2000),(1,32000)]:
 stable=[f for f in frames if index*12+6<=f['queued_index']<index*12+12]
 if not stable:continue
 total=sum(f['raw']['samples'] for f in stable)
 phases.append(dict(requested_exposure_us=exposure,stable_frames=len(stable),metadata_exposures_us=sorted(set(f['exposure_us'] for f in stable)),
  raw_mean=statistics.median(f['raw']['mean'] for f in stable),raw_stddev=statistics.median(f['raw']['stddev'] for f in stable),
  raw_min=min(f['raw']['min'] for f in stable),raw_max=max(f['raw']['max'] for f in stable),
  raw_fraction_le80=sum(n for f in stable for v,n in f['raw']['histogram'] if v<=80)/total,
  rgb_mean=statistics.median(f['rgb']['mean'] for f in stable),
  bayer_means=[statistics.median(f['bayer'][c]['mean'] for f in stable) for c in range(4)]))
time.sleep(1);after=subprocess.check_output(['dmesg'])
report=dict(stage=270,exit=q.returncode,paired_frames=len(frames),phases=phases,same_request_raw_rgb=True,
 runtime_after=Path('/sys/bus/i2c/devices/8-002d/power/runtime_status').read_text().strip(),
 fault_delta={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',fatal=b'fatal error received',modem=b'crash detected in modem').items()},
 taint=int(Path('/proc/sys/kernel/tainted').read_text()),scene_or_lighting_not_controlled=True,optical_usable_image_not_yet_proven=True)
(root/'summary.json').write_text(json.dumps(report,indent=2)+'\n');state.update(state='terminal',terminal=True,exit_code=q.returncode);(root/'state-private.json').write_text(json.dumps(state));print(json.dumps(report))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=80,check=False)
(host.PRIVATE/'telephoto-paired-response-private.log').write_bytes(q.stdout+q.stderr)
assert q.stdout,'Inspect the submitted probe and current boot; do not repeat the context'
d=json.loads(q.stdout);(R/'telephoto-paired-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
