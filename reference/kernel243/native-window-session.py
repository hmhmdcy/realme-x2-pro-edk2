"""Correlate one validated, bounded LOC session with AP clock/regulator events."""
from pathlib import Path
import dbus,hashlib,json,os,subprocess,time,traceback
os.umask(0o077)
root=Path('/var/lib/samurai');out=root/'k243-window-clock'
assert not out.exists();out.mkdir(mode=0o700)
state=dict(stage=243,state='preflight',terminal=False,pid=os.getpid())
def save():
 p=out/'state-next-private.json';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(out/'state-private.json')
save();instance=Path('/sys/kernel/tracing/instances/gnss243window');owned=False;child=None;bus=None;error=None
def snap(label):
 values={}
 for name,p in dict(clk='/sys/kernel/debug/clk/clk_summary',regulator='/sys/kernel/debug/regulator/regulator_summary',gpio='/sys/kernel/debug/gpio',genpd='/sys/kernel/debug/pm_genpd/pm_genpd_summary').items():
  values[name]=Path(p).read_text()
 values['monotonic_ns']=time.monotonic_ns()
 for name in ['tftp','rmtfs']:
  p=Path('/run/samurai-wifi')/(name+'.log')
  if p.is_file():
   assert p.stat().st_size<32*1024*1024
   (out/(label+'-'+name+'-private.log')).write_bytes(p.read_bytes())
 (out/(label+'-private.json')).write_text(json.dumps(values,indent=2)+'\n')
try:
 boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k236-runtime/boot-id-private.txt').read_bytes()
 tools=root/'k226-loc-tools-r3';binary=tools/'loc-session';build=json.loads((tools/'build-summary.json').read_text())
 assert hashlib.sha256(binary.read_bytes()).hexdigest()==build['binary_sha256']
 assert hashlib.sha256((tools/'loc-session.c').read_bytes()).hexdigest()==build['source_sha256']
 assert build['message_allowlist']==[33,34,35,50,51,63,75] and build['fixed_observation_seconds']==90
 bus=dbus.SystemBus(private=True);owner=str(bus.get_name_owner('org.freedesktop.ModemManager1'))
 objects=dbus.Interface(bus.get_object(owner,'/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
 paths=[str(p) for p,v in objects.items() if 'org.freedesktop.ModemManager1.Modem' in v];assert len(paths)==1
 props=dbus.Interface(bus.get_object(owner,paths[0]),'org.freedesktop.DBus.Properties');before=props.GetAll('org.freedesktop.ModemManager1.Modem.Location')
 assert int(before['Enabled'])==0 and not before['SignalsLocation'] and not bus.name_has_owner('org.freedesktop.GeoClue2')
 watch=json.loads((root/'gnss-assist/watch-state.json').read_text());assert not watch['active']
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 db=Path('/lib/apk/db/installed').read_bytes();dmesg=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(dmesg)
 assert not instance.exists();instance.mkdir();owned=True
 (instance/'tracing_on').write_text('0');(instance/'buffer_size_kb').write_text('1024');(instance/'trace_clock').write_text('mono')
 enabled=[]
 for group in ['clk','regulator']:
  for event in (instance/'events'/group).iterdir():
   if not (event/'format').is_file():continue
   fmt=(event/'format').read_text()
   if group=='clk':
    if 'char[] name;' not in fmt and 'char name[' not in fmt:continue
    names=['bi_tcxo','bi_tcxo_ao','rf_clk1','rf_clk1_ao','rf_clk2','rf_clk2_ao','rf_clk3','rf_clk3_ao','xo_board','gcc_mss_mfab_axis_clk','gcc_mss_cfg_ahb_clk']
    (event/'filter').write_text(' || '.join('name == "'+n+'"' for n in names))
   (event/'enable').write_text('1');enabled.append(group+'/'+event.name)
 (out/'enabled-events-private.json').write_text(json.dumps(enabled))
 snap('before');(instance/'tracing_on').write_text('1');(instance/'trace_marker').write_text('gnss243window-before-start\n')
 env=dict(os.environ);env.pop('LD_PRELOAD',None);env.pop('LD_LIBRARY_PATH',None)
 with (out/'events-private.jsonl').open('xb') as stdout,(out/'stderr-private.txt').open('xb') as stderr:
  start=time.monotonic();child=subprocess.Popen([str(binary),'high'],stdout=stdout,stderr=stderr,env=env)
  state.update(state='running',child_pid=child.pid,enabled_events=len(enabled));save()
  deadline=time.monotonic()+170;samples=set()
  while child.poll() is None:
   if time.monotonic()>=deadline:
    child.terminate();state.update(state='terminating');save();child.wait(timeout=40);raise RuntimeError('Bounded LOC deadline exceeded')
   for t in [5,30,75]:
    if t not in samples and time.monotonic_ns()/1e9-start>=t:
     (instance/'trace_marker').write_text('gnss243window-sample-'+str(t)+'\n');snap('active-'+str(t));samples.add(t)
   time.sleep(0.5)
  rc=child.returncode
 (instance/'trace_marker').write_text('gnss243window-after-close\n');snap('after')
 (instance/'tracing_on').write_text('0')
 (out/'trace-private.txt').write_text((instance/'trace').read_text())
 stats={str(p.parent.name):(p.read_text()) for p in (instance/'per_cpu').glob('cpu*/stats')}
 (out/'trace-stats-private.json').write_text(json.dumps(stats,indent=2)+'\n')
 records=[json.loads(line) for line in (out/'events-private.jsonl').read_text().splitlines()];closed=records[-1]
 after=props.GetAll('org.freedesktop.ModemManager1.Modem.Location');watchafter=json.loads((root/'gnss-assist/watch-state.json').read_text())
 afterlog=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(afterlog)
 report=dict(stage=243,program_exit=rc,cleanup=closed,enabled_trace_events=len(enabled),samples_taken=sorted(samples),
  no_trace_overrun=all('overrun: 0\n' in v and 'dropped events: 0\n' in v for v in stats.values()),
  same_boot=boot==Path('/proc/sys/kernel/random/boot_id').read_bytes(),taint=int(Path('/proc/sys/kernel/tainted').read_text()),
  mm_preserved=str(bus.get_name_owner('org.freedesktop.ModemManager1'))==owner and all(before[k]==after[k] for k in ['Enabled','SignalsLocation','GpsRefreshRate']),
  assist_preserved=not watchafter['active'] and all(watch[k]==watchafter[k] for k in ['worker_starts','worker_completions']),
  package_database_preserved=db==Path('/lib/apk/db/installed').read_bytes(),
  fault_delta={k:afterlog.count(v)-dmesg.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',dsp_fatal=b'fatal error received').items()},
  environment="indoor window opened; other phones receive GPS per user",clock_regulator_gpio_reads_only=True,no_nv_or_lock_configuration=True,android_capture=False)
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
 assert rc==0 and closed['stop_ack'] and closed['client_released'] and closed['device_closed']
 assert report['same_boot'] and report['mm_preserved'] and report['assist_preserved'] and report['package_database_preserved']
 assert report['taint']==0 and not any(report['fault_delta'].values()) and report['no_trace_overrun']
 state.update(state='terminal',terminal=True,exit_code=0);save()
except BaseException:
 error=traceback.format_exc();(out/'failure-private.txt').write_text(error)
 state.update(state='failed',terminal=child is None or child.poll() is not None,exit_code=1);save()
finally:
 if owned:
  (instance/'tracing_on').write_text('0')
  (instance/'events/enable').write_text('0')
  instance.rmdir()
  state['trace_instance_removed']=True;save()
 if bus:bus.close()
if error:raise SystemExit(1)
