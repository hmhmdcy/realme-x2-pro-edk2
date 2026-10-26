"""Bounded idle-only stack attribution; no GNSS start or regulator writes."""
from pathlib import Path
import dbus,json,os,re,subprocess,time,traceback
os.umask(0o077);r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
o=r/'k243-regulator-origin';assert not o.exists();o.mkdir(mode=0o700);instance=Path('/sys/kernel/tracing/instances/gnss243ldo');assert not instance.exists()
bus=dbus.SystemBus(private=True);objects=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();v=next(x for x in objects.values() if 'org.freedesktop.ModemManager1.Modem' in x);loc=v['org.freedesktop.ModemManager1.Modem.Location']
assert int(loc['Enabled'])==0 and not loc['SignalsLocation'] and not json.loads((r/'gnss-assist/watch-state.json').read_text())['active']
before=subprocess.check_output(['dmesg']);owned=False;triggered=False;error=None;raw='';stats={}
try:
 instance.mkdir();owned=True;(instance/'tracing_on').write_text('0');(instance/'buffer_size_kb').write_text('256')
 event=instance/'events/regulator/regulator_enable';supported=(event/'trigger').read_text();assert 'stacktrace' in supported
 (event/'trigger').write_text('stacktrace if name == "ldo10"');triggered=True;(event/'filter').write_text('name == "ldo10"');(event/'enable').write_text('1')
 (instance/'tracing_on').write_text('1');end=time.monotonic()+35
 while time.monotonic()<end:time.sleep(min(0.5,end-time.monotonic()))
 (instance/'tracing_on').write_text('0');raw=(instance/'trace').read_text();stats={p.parent.name:p.read_text() for p in (instance/'per_cpu').glob('cpu*/stats')}
except BaseException:error=traceback.format_exc();(o/'failure-private.txt').write_text(error)
finally:
 if owned:
  (instance/'tracing_on').write_text('0');(instance/'events/enable').write_text('0')
  if triggered:(instance/'events/regulator/regulator_enable/trigger').write_text('!stacktrace')
  instance.rmdir()
 bus.close()
after=subprocess.check_output(['dmesg']);(o/'trace-private.txt').write_text(raw);(o/'stats-private.json').write_text(json.dumps(stats,indent=2)+'\n')
symbols=re.findall(r'^\s*=>\s+([A-Za-z0-9_.]+)',raw,re.M)
report=dict(stage=243,idle_seconds=35,gnss_not_started=True,regulator_not_written=True,ldo10_enable_events=raw.count('regulator_enable: name=ldo10'),stack_symbols=sorted(set(symbols)),trace_removed=not instance.exists(),
 no_trace_overrun=bool(stats) and all('overrun: 0\n' in x and 'dropped events: 0\n' in x for x in stats.values()),failure=bool(error),taint=int(Path('/proc/sys/kernel/tainted').read_text()),
 fault_delta={k:after.count(t)-before.count(t) for k,t in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',dsp_fatal=b'fatal error received').items()})
(o/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'report':report,'private':{'trace':raw,'stats':stats,'failure':error}}))
