from pathlib import Path
import dbus,json,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k201-baseline/boot-id-private.txt').read_bytes()
out=root/'k201-validity-cli';assert not out.exists();out.mkdir(mode=0o700)
p=subprocess.run(['qmicli','-d','qrtr://0','--loc-get-predicted-orbits-data-validity'],capture_output=True,text=True,timeout=35)
(out/'result-private.txt').write_text(p.stdout+p.stderr)
bus=dbus.SystemBus(private=True);props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties');loc=props.GetAll('org.freedesktop.ModemManager1.Modem.Location');m=props.GetAll('org.freedesktop.ModemManager1.Modem');bus.close()
print(json.dumps(dict(stage=201,query_exit=p.returncode,query_result=p.stdout+p.stderr,gps_enabled=int(loc['Enabled']),refresh_rate=int(loc['GpsRefreshRate']),signals_location=bool(loc['SignalsLocation']),power=int(m['PowerState']))))
