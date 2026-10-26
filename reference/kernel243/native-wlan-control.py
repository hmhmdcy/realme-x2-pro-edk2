"""Temporarily soft-block only WLAN around one bounded standalone session."""
from pathlib import Path
import dbus,json,os,signal,subprocess,time,traceback
os.umask(0o077);r=Path('/var/lib/samurai');o=r/'k243-wlan-control';assert not o.exists();o.mkdir(mode=0o700)
state=dict(stage=243,state='preflight',terminal=False,pid=os.getpid());wlan=None;changed=False;child=None;error=None
def save():
 p=o/'state-next-private.json';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(o/'state-private.json')
def interrupted(signum,frame):raise KeyboardInterrupt('WLAN control interrupted')
signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted);save()
def flags():return {p.name:{k:(p/k).read_text().strip() for k in ['name','type','soft','hard']} for p in Path('/sys/class/rfkill').glob('rfkill*')}
before=flags();(o/'rfkill-before-private.json').write_text(json.dumps(before,indent=2)+'\n')
bus=dbus.SystemBus(private=True);props=dbus.Interface(bus.get_object('org.freedesktop.NetworkManager','/org/freedesktop/NetworkManager'),'org.freedesktop.DBus.Properties')
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
 candidates=[Path('/sys/class/rfkill')/n for n,v in before.items() if v['type']=='wlan'];assert len(candidates)==1;wlan=candidates[0]
 assert before[wlan.name]['soft']=='0' and before[wlan.name]['hard']=='0'
 assert props.Get('org.freedesktop.NetworkManager','WirelessEnabled') and props.Get('org.freedesktop.NetworkManager','WirelessHardwareEnabled')
 # The authenticated host transport is USB. Do not alter NM profiles or other RFKill types.
 changed=True;(wlan/'soft').write_text('1');time.sleep(1);assert (wlan/'soft').read_text().strip()=='1'
 blocked=flags();assert all(blocked[n]==v for n,v in before.items() if v['type']!='wlan')
 (o/'rfkill-active-private.json').write_text(json.dumps(blocked,indent=2)+'\n');state.update(state='wlan_blocked');save()
 with (o/'session-worker-private.log').open('xb') as log:
  child=subprocess.Popen(['python3',str(r/'k243-wlan-tools/native-wlan-session.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=log)
  state.update(state='session_running',child_pid=child.pid);save();deadline=time.monotonic()+190
  while child.poll() is None:
   if time.monotonic()>deadline:raise RuntimeError('WLAN experiment deadline')
   assert (wlan/'soft').read_text().strip()=='1'
   time.sleep(0.5)
  assert child.returncode==0
except BaseException:error=traceback.format_exc();(o/'failure-private.txt').write_text(error)
finally:
 try:
  if child and child.poll() is None:child.terminate();child.wait(timeout=40)
 finally:
  if changed:
   assert (wlan/'type').read_text().strip()=='wlan' and (wlan/'name').read_text().strip()==before[wlan.name]['name']
   (wlan/'soft').write_text(before[wlan.name]['soft']);state['wlan_restore_requested']=True;save()
 end=time.monotonic()+20
 while time.monotonic()<end and not props.Get('org.freedesktop.NetworkManager','WirelessEnabled'):time.sleep(0.5)
 after=flags();restored=after==before;nm_restored=bool(props.Get('org.freedesktop.NetworkManager','WirelessEnabled'));bus.close()
 report=dict(stage=243,wlan_softblock_single_variable=True,original_rfkill_restored=restored,networkmanager_radio_enabled_restored=nm_restored,non_wlan_rfkill_preserved=all(after[n]==v for n,v in before.items() if v['type']!='wlan'),worker_exit=child.returncode if child else None,failure=bool(error),no_nv_or_package_changes=True)
 (o/'summary.json').write_text(json.dumps(report,indent=2)+'\n');(o/'rfkill-after-private.json').write_text(json.dumps(after,indent=2)+'\n')
 state.update(state='terminal' if restored and nm_restored and not error else 'failed',terminal=child is None or child.poll() is not None,exit_code=0 if restored and nm_restored and not error else 1);save()
if state['exit_code']:raise SystemExit(1)
