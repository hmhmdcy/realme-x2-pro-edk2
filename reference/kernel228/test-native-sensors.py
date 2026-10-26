"""Real open/close module pinning, five SSC streams and ordinary-user claims."""
from pathlib import Path
import json
import host

code = r'''
from pathlib import Path
import dbus,errno,hashlib,json,os,pwd,subprocess,time,traceback
root=Path('/var/lib/samurai');out=root/'k228-native-sensors';assert not out.exists()
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k228-runtime/boot-id-private.txt').read_bytes()
assert int(Path('/proc/sys/kernel/tainted').read_text())==4096
assert {p.parent.name:p.read_text().strip() for p in Path('/sys/module').glob('*/taint') if p.read_text().strip()}=={'fastrpc':'O'}
out.mkdir(mode=0o700);(out/'boot-id-private.txt').write_bytes(boot)
state=dict(state='running',pid=os.getpid(),start_ticks=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]);(out/'state-private.json').write_text(json.dumps(state)+'\n')
before=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(before)
ssc_before=json.loads(Path('/run/samurai-ssc/state.json').read_text());assert ssc_before['started']
try:
 ref=lambda:int(Path('/sys/module/fastrpc/refcnt').read_text())
 baseline=ref();assert baseline>=1
 pin=None;attempts=[]
 for name in ['fastrpc-adsp','fastrpc-cdsp','fastrpc-cdsp-secure','fastrpc-sdsp']:
  p=Path('/dev')/name
  if not p.exists():continue
  try:fd=os.open(p,os.O_RDWR|os.O_CLOEXEC)
  except OSError as e:
   attempts.append(dict(device=name,errno=e.errno));assert e.errno in (errno.EBUSY,errno.ENODEV,errno.EACCES);continue
  try:
   during=ref();assert during==baseline+1
   pin=dict(device=name,before=baseline,while_open=during)
  finally:os.close(fd)
  after=ref();assert after==baseline;pin['after_close']=after
  break
 assert pin is not None,'No free session to verify reference delta'
 streams={};env=dict(os.environ,LD_LIBRARY_PATH='/usr/lib/samurai/ssc',LIBSSC_LIGHT_DATA_TYPE='wise_light')
 for name,label in [('accelerometer','Accelerometer'),('gyroscope','Gyroscope'),('magnetometer','Magnetometer'),('light','Light'),('proximity','Proximity')]:
  result=subprocess.run(['ssccli','--debug','--sensor',name,'--timeout','2'],capture_output=True,env=env,timeout=20)
  raw=result.stdout+result.stderr;(out/(name+'-private.log')).write_bytes(raw);text=raw.decode(errors='replace')
  count=text.count(label+' sensor measurement:');disabled=(label+' sensor disabled').lower() in text.lower()
  assert result.returncode==0 and count>0 and disabled,name
  streams[name]=dict(measurements=count,clean_disable=True,exit_code=0)
 user=pwd.getpwuid(10000)
 def demote():
  os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(10000)
 claim_code="""import dbus,json,os,time
assert os.getuid()==10000
b=dbus.SystemBus(private=True);o=b.get_object('net.hadess.SensorProxy','/net/hadess/SensorProxy');i=dbus.Interface(o,'net.hadess.SensorProxy');p=dbus.Interface(o,'org.freedesktop.DBus.Properties')
has={n:bool(p.Get('net.hadess.SensorProxy',n)) for n in ['HasAccelerometer','HasAmbientLight','HasProximity']};assert all(has.values())
done=[]
for claim,release in [('ClaimAccelerometer','ReleaseAccelerometer'),('ClaimLight','ReleaseLight'),('ClaimProximity','ReleaseProximity')]:
 getattr(i,claim)(timeout=15)
 try:time.sleep(1)
 finally:getattr(i,release)(timeout=15)
 done.append(claim)
b.close();print(json.dumps(dict(uid=10000,has=has,claimed_and_released=done)))
"""
 result=subprocess.run(['/usr/bin/python3','-c',claim_code],capture_output=True,preexec_fn=demote,cwd='/tmp',timeout=60)
 (out/'ordinary-user-claims-private.log').write_bytes(result.stdout+result.stderr);assert result.returncode==0
 claims=json.loads(result.stdout);assert len(claims['claimed_and_released'])==3
 ssc_after=json.loads(Path('/run/samurai-ssc/state.json').read_text());assert all(ssc_before[k]==ssc_after[k] for k in ['pid','start_ticks','boot_id']) and ssc_after['started']
 assert ref()==baseline
 afterlog=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(afterlog)
 patterns=dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed')
 faults={k:afterlog.count(v)-before.count(v) for k,v in patterns.items()};assert not any(faults.values())
 assert int(Path('/proc/sys/kernel/tainted').read_text())==4096 and Path('/sys/module/fastrpc/taint').read_text().strip()=='O'
 assert boot==Path('/proc/sys/kernel/random/boot_id').read_bytes()
 report=dict(stage=228,new_boot228=True,loaded_candidate='7ca5d442',real_module_pin=pin,failed_open_attempts=attempts,
  five_real_sensor_streams=streams,ordinary_uid10000_claims=claims,ssc_daemon_identity_preserved=True,
  module_refcount_final=ref(),fault_increments=faults,taint=4096,taint_reason='external M= module O flag only',
  hardware_accuracy_motion_orientation_not_validated=True,no_ssr_or_unload=True)
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');state.update(state='terminal',exit_code=0);(out/'state-private.json').write_text(json.dumps(state)+'\n');print(json.dumps(report))
except BaseException:
 (out/'failure-private.txt').write_text(traceback.format_exc());state.update(state='terminal',exit_code=1);(out/'state-private.json').write_text(json.dumps(state)+'\n');raise
'''
result = host.ssh('python3 -', input=code.encode(), timeout=130)
(host.PRIVATE / 'native-sensors-host-private.log').write_bytes(result.stdout + result.stderr)
report = json.loads(result.stdout)
(Path(__file__).resolve().parent / 'native-sensors-validation.json').write_text(json.dumps(report, indent=2) + '\n')
state = json.loads((host.PRIVATE / 'current-work-private.json').read_text())
state.update(state='new candidate pins1to2to1; five SSC and ordinary UID10000 claims passed; only OOT taint4096, in-tree build needed',
             active_native_session=None, active_native_context=None,runtime_deployed=True,
             next='Build accepted source through in-tree target to obtain real intree metadata; preserve old/candidate sources and all unrelated kernel artifacts; next clean controlled boot')
(host.PRIVATE / 'current-work-private.json').write_text(json.dumps(state, indent=2) + '\n')
print(json.dumps(report))
