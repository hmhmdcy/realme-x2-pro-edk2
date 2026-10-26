"""Submit one bounded baseline per mode on the existing guarded boot."""
from pathlib import Path
import json, shlex, hashlib, sys
import host

R = Path(__file__).resolve().parent
proof = json.loads((R / 'control-probe-build-validation.json').read_text())
mode = sys.argv[1]
assert mode in ['manual', 'auto']
label = 'baseline-' + mode + '-r1'
response = host.PRIVATE / (label + '-response-private.log')
assert not response.exists(), 'Inspect the original submitted context instead of repeating it'
if mode == 'manual':
    binary = (host.PRIVATE / 'telephoto-control-probe271').read_bytes()
    assert hashlib.sha256(binary).hexdigest() == proof['binary_sha256']
    code = "from pathlib import Path;import os;os.umask(0o077);p=Path('/run/samurai-camera271-probes');p.mkdir(mode=0o755);p.chmod(0o755);(p/'telephoto-control-probe271').write_bytes(b'')"
    host.ssh('python3 -c ' + shlex.quote(code), timeout=20)
    for offset in range(0, len(binary), 24576):
        code = "from pathlib import Path;import sys;p=Path('/run/samurai-camera271-probes/telephoto-control-probe271');assert p.stat().st_size==%d;f=p.open('ab');f.write(sys.stdin.buffer.read());f.close()" % offset
        host.ssh('python3 -c ' + shlex.quote(code), input=binary[offset:offset+24576], timeout=20)
    code = "from pathlib import Path;import hashlib;p=Path('/run/samurai-camera271-probes/telephoto-control-probe271');assert hashlib.sha256(p.read_bytes()).hexdigest()==%r;p.chmod(0o755)" % proof['binary_sha256']
    host.ssh('python3 -c ' + shlex.quote(code), timeout=20)
else:
    manual = json.loads((R / 'baseline-manual-r1-validation.json').read_text())
    settled = json.loads((R / 'baseline-settled-r1-validation.json').read_text())
    assert manual['exit'] == 0 and manual['paired_frames'] == 96 and settled['passed']

code = r'''
from pathlib import Path
import hashlib,json,os,pwd,statistics,subprocess,time,traceback
mode=__MODE__;label='baseline-'+mode+'-r1'
os.umask(0o077);root=Path('/var/lib/samurai/k271-'+label);root.mkdir(mode=0o700)
state=dict(state='preflight',terminal=False,pid=os.getpid())
def save():(root/'state-private.json').write_text(json.dumps(state))
def fault_counts():
 b=subprocess.check_output(['dmesg'])
 return {k:b.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',fatal=b'fatal error received',modem=b'crash detected in modem').items()}
def health():
 runtime={}
 for bus,names in [('i2c',['7-0010','8-002d','9-0010']),('platform',['ac4a000.cci','ac4b000.cci','acb3000.camss'])]:
  for n in names:runtime[n]=Path('/sys/bus',bus,'devices',n,'power/runtime_status').read_text().strip()
 rails={}
 for p in Path('/sys/class/regulator').glob('regulator.*'):
  n=(p/'name').read_text().strip()
  if n.startswith(('cam-front-','cam-rear-','cam-tele-')):rails[n]={k:(p/k).read_text().strip() for k in ['state','num_users']}
 clocks=Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines()
 mclk={n:int(next(l.split()[1] for l in clocks if l.split() and l.split()[0]==n)) for n in ['cam_cc_mclk1_clk','cam_cc_mclk2_clk','cam_cc_mclk3_clk']}
 faults={k:v-before[k] for k,v in fault_counts().items()};taint=int(Path('/proc/sys/kernel/tainted').read_text())
 passed=not any(faults.values()) and taint==0 and all(v=='suspended' for v in runtime.values()) and len(rails)==6 and all(v['state']=='disabled' and v['num_users']=='0' for v in rails.values()) and not any(mclk.values())
 return dict(runtime=runtime,rails=rails,mclk=mclk,fault_delta=faults,taint=taint,passed=passed)
def percentile(histogram,quantile):
 total=sum(n for _,n in histogram);threshold=total*quantile;count=0
 for value,n in histogram:
  count+=n
  if count>=threshold:return value
def summarize(frames):
 total=sum(f['raw']['samples'] for f in frames)
 return dict(frames=len(frames),exposure_us=sorted(set(f['exposure_us'] for f in frames)),gains=sorted(set(f['analogue_gain'] for f in frames)),
 raw_mean=statistics.median(f['raw']['mean'] for f in frames),raw_stddev=statistics.median(f['raw']['stddev'] for f in frames),
 raw_p90=statistics.median(percentile(f['raw']['histogram'],.9) for f in frames),raw_p99=statistics.median(percentile(f['raw']['histogram'],.99) for f in frames),
 raw_clipped_fraction=sum(n for f in frames for value,n in f['raw']['histogram'] if value>=1020)/total,
 rgb_mean=statistics.median(f['rgb']['mean'] for f in frames),rgb_p90=statistics.median(percentile(f['rgb']['histogram'],.9) for f in frames))
save();before=fault_counts()
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k270-work/boot-id-private.txt').read_bytes()
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 module=Path('/usr/lib/modules')/os.uname().release/'kernel/drivers/media/i2c/s5k3m5.ko'
 assert hashlib.sha256(module.read_bytes()).hexdigest()=='22315c6f3eb233add16e33658bd071dbc973499744b21323adf8b771c1552f72'
 binary=Path('/run/samurai-camera271-probes/telephoto-control-probe271');assert hashlib.sha256(binary.read_bytes()).hexdigest()==__SHA__
 for p in Path('/proc').glob('[0-9]*'):
  try:name=(p/'comm').read_text().strip()
  except OSError:continue
  assert name not in ['snapshot','cam','gst-launch-1.0','telephoto-paire','telephoto-contr'],'Camera client active'
 assert health()['passed']
 u=pwd.getpwuid(10000)
 def demote():os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid)
 node=next('/dev/'+p.name for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='s5k3m5 8-002d')
 assert 'test_pattern: 0' in subprocess.check_output(['v4l2-ctl','-d',node,'--get-ctrl=test_pattern'],text=True)
 state['state']='capturing';save()
 q=subprocess.run([str(binary),node,'/base/soc@0/cci@ac4b000/i2c-bus@0/camera@2d','s5k3m5','s5k3m5 8-002d','rgb','2048','1536',mode],
  preexec_fn=demote,env=dict(PATH='/usr/bin:/bin',HOME=u.pw_dir,LIBCAMERA_LOG_LEVELS='*:INFO,IPASoftExposure:DEBUG'),capture_output=True,timeout=115)
 (root/'stdout-private.json').write_bytes(q.stdout);(root/'stderr-private.log').write_bytes(q.stderr)
 frames=json.loads(q.stdout)['frames'] if q.stdout else []
 chunks=[]
 for start in range(0,len(frames),12):
  stable=frames[start+6:start+12]
  if stable:chunks.append(dict(first_queued_index=start,**summarize(stable)))
 deltas=[b['timestamp_ns']-a['timestamp_ns'] for a,b in zip(frames,frames[1:])]
 time.sleep(1)
 report=dict(stage=271,mode=mode,exit=q.returncode,paired_frames=len(frames),phases=chunks,
  median_frame_interval_ns=statistics.median(deltas) if deltas else None,first_sequence=frames[0]['sequence'] if frames else None,last_sequence=frames[-1]['sequence'] if frames else None,
  health=health(),lighting_user_reported_not_measured=True,no_pixels_saved_by_probe=True)
 (root/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
 state.update(state='terminal',terminal=True,exit_code=q.returncode);save();print(json.dumps(report))
except BaseException:
 (root/'failure-private.txt').write_text(traceback.format_exc());state.update(state='failed',terminal=True,exit_code=1);save();raise
'''.replace('__MODE__', repr(mode)).replace('__SHA__', repr(proof['binary_sha256']))
response.write_bytes(b'SUBMISSION INTENT: inspect the existing device context if the response is lost.\n')
q = host.ssh('python3 -', input=code.encode(), timeout=140, check=False)
response.write_bytes(q.stdout + q.stderr)
assert q.returncode == 0 and q.stdout, 'Inspect submitted context before any other capture'
d = json.loads(q.stdout)
(R / (label + '-validation.json')).write_text(json.dumps(d, indent=2)+'\n')
print(json.dumps(d, indent=2))
