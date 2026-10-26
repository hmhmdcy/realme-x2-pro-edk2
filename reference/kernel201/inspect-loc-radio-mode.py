from pathlib import Path
import dbus,json,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k201-baseline/boot-id-private.txt').read_bytes()
out=root/'k201-loc-radio-mode';assert not out.exists();out.mkdir(mode=0o700)
report=dict(stage=201,read_only=True,queries={})
for option in ['dms-get-operating-mode','loc-get-operation-mode','loc-get-engine-lock']:
 p=subprocess.run(['qmicli','-d','qrtr://0','--'+option],capture_output=True,text=True,timeout=30);text=p.stdout+p.stderr;(out/(option+'-private.txt')).write_text(text);report['queries'][option]=dict(exit=p.returncode,result=text)
bus=dbus.SystemBus(private=True);mp=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties');report['gps_enabled']=int(mp.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'));report['power']=int(mp.Get('org.freedesktop.ModemManager1.Modem','PowerState'));bus.close();(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
