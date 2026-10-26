"""Exercise real managed links per device; capture only reset GPIO trace events."""
from pathlib import Path
import hashlib,json,os,pwd,re,signal,subprocess,time,traceback
root=Path('/var/lib/samurai');out=root/'k233-pmic-cycles'
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k233-runtime/boot-id-private.txt').read_bytes()
assert json.loads((root/'k233-runtime/state-private.json').read_text())['exit_code']==0
assert not out.exists();out.mkdir(mode=0o700);(out/'boot-id-private.txt').write_bytes(boot)
state=dict(state='running',phase='preflight',pid=os.getpid(),start_ticks=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19])
def phase(name,**kw):
 state.update(phase=name,**kw);temp=out/'state-new-private.json';temp.write_text(json.dumps(state,indent=2)+'\n');os.replace(temp,out/'state-private.json')
phase('preflight')
qname=json.loads((root/'k233-baseline/pmic-q-before-private.json').read_text())['device'];pname=qname.rsplit('-',1)[0]+'-0008'
q=Path('/sys/bus/i2c/devices')/qname;p=Path('/sys/bus/i2c/devices')/pname
provider=Path('/sys/bus/platform/devices/camera-pmic-resets')
driver=Path('/sys/bus/i2c/drivers/pm8008');reset_driver=Path('/sys/bus/platform/drivers/rmx1931-pm8008-resets')
sensor=Path('/sys/bus/i2c/devices/7-0010');sensor_driver=Path('/sys/bus/i2c/drivers/imx471')
trace=Path('/sys/kernel/tracing/instances/pmic233');trace_created=False;policy_context=None;front_detached=False
before=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(before)
def processes(name):
 result=[]
 for f in Path('/proc').iterdir():
  if not f.name.isdigit():continue
  try:
   if (f/'comm').read_text().strip()==name and int((f/'status').read_text().split('Uid:',1)[1].split()[0])==10000:result.append(f)
  except OSError:pass
 return result
def identities(name):return {f.name:(f/'stat').read_text().rsplit(')',1)[1].split()[19] for f in processes(name)}
desktop={n:identities(n) for n in ['pipewire','phosh','phoc']};assert all(len(v)==1 for v in desktop.values())
def bound(node):return (node/'driver').is_symlink()
def wait_for(predicate,seconds=12):
 end=time.monotonic()+seconds
 while not predicate() and time.monotonic()<end:time.sleep(.1)
 assert predicate(),'Binding state did not settle'
def idle():
 if bound(sensor):assert (sensor/'power/runtime_status').read_text().strip()=='suspended'
 for f in Path('/proc').iterdir():
  if not f.name.isdigit():continue
  try:
   for fd in (f/'fd').iterdir():
    try:assert not os.readlink(fd).startswith(('/dev/media','/dev/video','/dev/v4l-subdev'))
    except OSError:pass
  except OSError:pass
def rails():
 result={}
 for r in Path('/sys/class/regulator').glob('regulator.*'):
  if q.resolve() in r.resolve().parents:
   v={k:(r/k).read_text().strip() for k in ['name','state','num_users','microvolts'] if (r/k).exists()};result[v.pop('name')]=v
 return result
def check_p_no_children():
 assert not any(p.resolve() in n.resolve().parents for n in Path('/sys/bus/platform/devices').iterdir())
 assert not any(p.resolve() in n.resolve().parents for n in Path('/sys/class/regulator').glob('regulator.*'))
 assert not Path('/sys/bus/i2c/devices',qname.rsplit('-',1)[0]+'-0009').exists()
def reset_bound():return all(bound(n) for n in [p,q,provider])
def mark(name):
 phase(name);(trace/'trace_marker').write_text(name)
def resume_policy():
 if policy_context is None:return
 existing=processes('wireplumber');assert len(existing)<=1
 if existing:return
 user=pwd.getpwuid(10000)
 def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
 with (out/'policy-restart-private.log').open('ab') as log:
  child=subprocess.Popen(policy_context['argv'],env=policy_context['env'],preexec_fn=demote,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 time.sleep(2);assert child.poll() is None and len(processes('wireplumber'))==1
success=False;warm={};cold={};trace_text='';recovery=[]
try:
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and reset_bound()
 assert Path('/sys/module/qcom_pm8008/parameters/experimental_p_address_only').read_text().strip()=='Y'
 wp=processes('wireplumber');assert len(wp)==1;wp=wp[0]
 policy_context=dict(argv=[v.decode() for v in (wp/'cmdline').read_bytes().split(b'\0') if v],
  env={k.decode():v.decode() for value in (wp/'environ').read_bytes().split(b'\0') if b'=' in value for k,v in [value.split(b'=',1)]},
  pid=int(wp.name),start_ticks=(wp/'stat').read_text().rsplit(')',1)[1].split()[19])
 assert policy_context['argv']==['/usr/bin/wireplumber']
 assert not any(n in policy_context['env'] for n in ['LD_LIBRARY_PATH','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_IPA_PROXY_PATH','LIBCAMERA_IPA_CONFIG_PATH'])
 (out/'policy-context-private.json').write_text(json.dumps(policy_context,indent=2)+'\n')
 phase('policy_stop_submitted');os.kill(int(wp.name),signal.SIGTERM);wait_for(lambda:not wp.exists(),6)
 time.sleep(.5);assert not processes('wireplumber');idle()
 assert all(v.read_text().strip()=='closed' for v in Path('/proc/asound').glob('card*/pcm*/sub*/status'))
 initial_rails=rails();assert len(initial_rails)==7 and all(v['state']=='disabled' and v['num_users']=='0' for v in initial_rails.values())
 phase('front_unbind_submitted');(sensor_driver/'unbind').write_text('7-0010');front_detached=True;assert not bound(sensor)
 assert not trace.exists();trace.mkdir();trace_created=True
 (trace/'tracing_on').write_text('0');(trace/'buffer_size_kb').write_text('128')
 clocks=(trace/'trace_clock').read_text();assert 'global' in clocks;(trace/'trace_clock').write_text('global')
 (trace/'events/gpio/gpio_value/filter').write_text('get == 0')
 (trace/'events/gpio/gpio_value/enable').write_text('1');(trace/'events/gpio/gpio_direction/enable').write_text('1')
 (trace/'trace').write_text('');(trace/'tracing_on').write_text('1')
 warm_before=subprocess.check_output(['dmesg']);mark('Q_UNBIND_BEGIN');idle()
 (driver/'unbind').write_text(qname)
 assert not bound(q) and not bound(p) and bound(provider);mark('Q_UNBOUND')
 mark('Q_BIND_BEGIN');(driver/'bind').write_text(qname);wait_for(reset_bound);mark('Q_BOUND')
 check_p_no_children();warm_rails=rails();assert warm_rails==initial_rails
 warm_after=subprocess.check_output(['dmesg']);assert warm_after.count(b'assigned PM8008 primary address')==warm_before.count(b'assigned PM8008 primary address')
 assert warm_after.count(b'dependent PMIC identity verified; address-only bring-up, no children')==warm_before.count(b'dependent PMIC identity verified; address-only bring-up, no children')+1
 warm=dict(q_unbind_removed_p_first=True,provider_kept_bound=True,q_rebind_p_autoprobe=True,
  all_seven_q_rail_states_and_voltages_preserved=True,no_cold_address_assignment_log=True,p_identity_repeated=True)
 # All seven Q rails are idle before deliberately resetting the provider.
 assert all(v['state']=='disabled' and v['num_users']=='0' for v in rails().values())
 cold_before=warm_after;mark('PROVIDER_UNBIND_BEGIN');idle()
 (reset_driver/'unbind').write_text(provider.name)
 assert not any(bound(n) for n in [provider,p,q]);mark('PROVIDER_UNBOUND')
 mark('PROVIDER_BIND_BEGIN');(reset_driver/'bind').write_text(provider.name);wait_for(reset_bound);mark('PROVIDER_BOUND')
 check_p_no_children();cold_rails=rails();assert len(cold_rails)==7 and all(v['state']=='disabled' and v['num_users']=='0' for v in cold_rails.values())
 cold_after=subprocess.check_output(['dmesg'])
 assert cold_after.count(b'assigned PM8008 primary address')==cold_before.count(b'assigned PM8008 primary address')+1
 assert cold_after.count(b'dependent PMIC identity verified; address-only bring-up, no children')==cold_before.count(b'dependent PMIC identity verified; address-only bring-up, no children')+1
 cold=dict(provider_unbind_removed_p_and_q=True,provider_rebind_restored_q_and_p=True,
  one_cold_address_assignment=True,p_identity_repeated=True,all_seven_q_rails_off_zero_users=True)
 mark('CYCLES_COMPLETE');success=True
except BaseException:
 (out/'failure-private.txt').write_text(traceback.format_exc())
finally:
 if trace_created:
  (trace/'tracing_on').write_text('0');trace_text=(trace/'trace').read_text();(out/'gpio-trace-private.txt').write_text(trace_text)
  (trace/'events/gpio/gpio_value/enable').write_text('0');(trace/'events/gpio/gpio_direction/enable').write_text('0')
 # Restore only currently unbound devices; never repeat an in-flight operation.
 try:
  phase('restoring_bindings')
  if not bound(provider):(reset_driver/'bind').write_text(provider.name);recovery.append('provider')
  if not bound(q):(driver/'bind').write_text(qname);recovery.append('q')
  wait_for(reset_bound)
  if front_detached and not bound(sensor):(sensor_driver/'bind').write_text('7-0010')
  wait_for(lambda:bound(sensor) and (sensor/'power/runtime_status').read_text().strip()=='suspended',6)
  resume_policy()
 except BaseException:
  (out/'restore-failure-private.txt').write_text(traceback.format_exc());success=False
 # Leave no tracing active. Preserve tracefs instance if removal is busy.
 if trace_created:
  try:trace.rmdir()
  except OSError:pass
try:
 assert success,'Inspect preserved native cycle failure; do not replay'
 # GPIO integer ids are learned from synchronous per-device operations;
 # GPIO tracepoints report software operations, not pad voltage readback.
 segments={};current=None
 for line in trace_text.splitlines():
  if 'tracing_mark_write:' in line:
   current=line.split('tracing_mark_write:',1)[1].strip();segments.setdefault(current,[])
  if current and 'gpio_value:' in line:
   match=re.search(r'gpio_value:\s*(\d+)\s+set\s+(-?\d+)',line)
   if match:segments[current].append((int(match[1]),int(match[2]),line))
 mine=lambda rows:[(n,v) for n,v,l in rows if re.search(r'-\s*'+str(os.getpid())+r'\s',l)]
 first=mine(segments['Q_UNBIND_BEGIN']);assert len(first)==1 and first[0][1]==0
 p_gpio=first[0][0];warm_outputs=mine(segments['Q_BIND_BEGIN']);assert warm_outputs and warm_outputs[0][1]==1
 q_gpio=warm_outputs[0][0];assert p_gpio!=q_gpio
 provider_outputs=mine(segments['PROVIDER_UNBIND_BEGIN'])
 selected=[('P' if n==p_gpio else 'Q',v) for n,v in provider_outputs if n in [p_gpio,q_gpio]]
 assert selected==[('P',0),('P',0),('Q',0)],selected
 assert not any(n==q_gpio and v==0 for n,v,l in segments['Q_BIND_BEGIN'])
 cold_outputs=[('P' if n==p_gpio else 'Q',v) for n,v,l in segments['PROVIDER_BIND_BEGIN'] if n in [p_gpio,q_gpio]]
 q_assert=cold_outputs.index(('Q',0));q_release=cold_outputs.index(('Q',1));p_release=cold_outputs.index(('P',1))
 assert q_assert<q_release<p_release
 direction_errors=[l for l in trace_text.splitlines() if re.search(r'gpio_direction:\s*(?:'+str(p_gpio)+'|'+str(q_gpio)+r')\s+out\s+\((-?\d+)\)',l) and not l.rstrip().endswith('(0)')]
 assert direction_errors==[]
 after=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(after)
 faults={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()}
 assert not any(faults.values()) and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 assert all(identities(n)==v for n,v in desktop.items()) and len(processes('wireplumber'))==1
 assert boot==Path('/proc/sys/kernel/random/boot_id').read_bytes()
 report=dict(stage=233,q_warm_cycle=warm,provider_cold_cycle=cold,
  native_gpio_trace=dict(p_cleanup_before_q_removed=True,provider_unbind_outputs=selected,
    provider_bind_outputs=cold_outputs,q_assert_before_release_before_p_release=True,software_trace_not_physical_pad_readback=True),
  p_has_no_mfd_or_regulator_children=True,front_sensor_rebound_and_suspended=True,wireplumber_restored=True,
  desktop_pipewire_processes_unchanged=True,module_files_unchanged=True,explicit_recovery_binds=recovery,
  taint=0,fault_delta=faults,scene_capture_not_performed=True)
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');phase('complete',state='terminal',exit_code=0)
except BaseException:
 (out/'validation-failure-private.txt').write_text(traceback.format_exc());phase('failed',state='terminal',exit_code=1);raise
