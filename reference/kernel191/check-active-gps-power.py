"""Observe DMS mode during an MM GPS session; do not change modem power mode."""
from pathlib import Path
import dbus,json,os,subprocess,time
os.umask(0o077)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
out=Path('/var/lib/samurai/k191-active-power');out.mkdir(mode=0o700)
bus=dbus.SystemBus(private=True);service='org.freedesktop.ModemManager1';obj=bus.get_object(service,'/org/freedesktop/ModemManager1/Modem/0')
props=dbus.Interface(obj,'org.freedesktop.DBus.Properties');api=dbus.Interface(obj,service+'.Modem.Location')
assert int(props.Get(service+'.Modem.Location','Enabled'))==0
report=dict(stage=191,mode_set_requests_sent=False,samples=[],gps_setup_ack=False,gps_cleanup_ack=False)
try:
 api.Setup(dbus.UInt32(6),dbus.Boolean(False),timeout=30);report['gps_setup_ack']=True
 for index,delay in enumerate([2,12]):
  time.sleep(delay)
  p=subprocess.run(['qmicli','-d','qrtr://0','--dms-get-operating-mode'],capture_output=True,timeout=25)
  (out/('mode-'+str(index)+'-private.txt')).write_bytes(p.stdout+p.stderr);text=p.stdout.decode().lower()
  mode=next((name for name in ['online','low-power','offline','resetting','shutting-down','persistent-low-power','mode-only-low-power'] if "'"+name+"'" in text),None)
  report['samples'].append(dict(exit=p.returncode,dms_mode=mode,gps_enabled=int(props.Get(service+'.Modem.Location','Enabled')),mm_power_state=int(props.Get(service+'.Modem','PowerState'))))
finally:
 if report['gps_setup_ack']:api.Setup(dbus.UInt32(0),dbus.Boolean(False),timeout=30);report['gps_cleanup_ack']=True
 report['final_enabled']=int(props.Get(service+'.Modem.Location','Enabled'));bus.close()
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report));assert report['gps_cleanup_ack'] and report['final_enabled']==0
